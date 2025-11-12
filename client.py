import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

# Redis import (optional)
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# MySQL import (optional)
try:
    import aiomysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    aiomysql = None

# Load client-specific environment variables
load_dotenv(".env.client")

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
CLIENT_PORT = int(os.getenv("CLIENT_PORT", "8001"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "mcp_chat")
MYSQL_USER = os.getenv("MYSQL_USER", "mcp_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", "5"))

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Redis client
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        logger.info(f"Redis client initialized at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        redis_client = None

# MySQL connection pool
mysql_pool = None

# Pydantic Models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message/question")
    session_id: str = Field(default="default", description="Session identifier")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI response")
    tools_used: List[str] = Field(default=[], description="List of tools used")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")
    interaction_id: Optional[str] = Field(None, description="Unique interaction ID for logging")
    debug: Optional[Dict[str, Any]] = Field(None, description="Debug information")

class InteractionLog(BaseModel):
    interaction_id: str
    session_id: str
    timestamp: str
    user_message: str
    llm_payload: Optional[Dict[str, Any]] = None
    llm_response: Optional[str] = None
    tools_used: List[str] = []
    tool_results: Optional[Dict[str, Any]] = None
    final_response: str
    feedback: Optional[str] = None  # "thumbs_up", "thumbs_down", or None

class FeedbackRequest(BaseModel):
    interaction_id: str
    session_id: str
    feedback: str  # "thumbs_up" or "thumbs_down"

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

# FastAPI App
app = FastAPI(
    title="MCP Client - Ollama Integration",
    version="1.0.0",
    description="A client that integrates Ollama LLM with MCP server tools"
)

# Add CORS middleware to allow requests from the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MCPClient:
    """Client for interacting with the MCP server."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    async def get_available_tools(self) -> List[ToolInfo]:
        """Fetch available tools from MCP server."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/v1/tools/list")
                response.raise_for_status()
                tools_data = response.json()
                return [ToolInfo(**tool) for tool in tools_data]
            except Exception as e:
                logger.error(f"Failed to fetch tools: {e}")
                return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute a tool on the MCP server."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "session_id": session_id
                }
                response = await client.post(f"{self.base_url}/v1/tools/call", json=payload)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to call tool {tool_name}: {e}")
                return {"status": "error", "result_data": {"error": str(e)}}

class OllamaClient:
    """Client for interacting with Ollama."""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
        
    async def generate(self, prompt: str, tools_context: str = "") -> str:
        """Generate response using Ollama."""
        result = await self.generate_with_details(prompt, tools_context)
        return result["response"]
    
    async def generate_with_details(self, prompt: str, tools_context: str = "") -> Dict[str, Any]:
        """Generate response using Ollama and return full details."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Construct the full prompt with tools context
                full_prompt = self._build_prompt(prompt, tools_context)
                
                payload = {
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False
                }
                
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "full_prompt": full_prompt,
                    "response": result.get("response", "No response generated"),
                    "model": self.model,
                    "tools_context": tools_context
                }
                
            except httpx.TimeoutException:
                return {
                    "full_prompt": full_prompt if 'full_prompt' in locals() else prompt,
                    "response": "Request timed out. Please try again.",
                    "model": self.model,
                    "error": "timeout"
                }
            except Exception as e:
                logger.error(f"Ollama generation failed: {e}")
                return {
                    "full_prompt": full_prompt if 'full_prompt' in locals() else prompt,
                    "response": f"Error generating response: {str(e)}",
                    "model": self.model,
                    "error": str(e)
                }
    
    def _build_prompt(self, user_message: str, tools_context: str = "") -> str:
        """Build the complete prompt for Ollama."""
        if tools_context:
            # Second call - we have tool results, provide a complete answer
            return f"""Based on the tool results below, provide a helpful answer to the user's question.

Tool Results:
{tools_context}

User Question: {user_message}

Provide a clear, helpful response using the information from the tools."""
        else:
            # First call - determine if we need tools
            return f"""You are an AI assistant with access to network and smart home tools. Analyze the user's request and respond appropriately.

User request: "{user_message}"

Available Tools:
1. get_network_time - Get current accurate time from NTP server
2. ping_host - Test network connectivity to a hostname
3. ha_get_device_state - Get state of Home Assistant devices/sensors (temperature, humidity, status)
4. ha_control_light - Control Home Assistant lights (turn on/off, brightness)
5. ha_control_switch - Control Home Assistant switches (turn on/off)

Instructions:
- For time/date queries: USE_TOOL:get_network_time:{{}}
- For ping/connectivity: USE_TOOL:ping_host:{{"hostname": "HOSTNAME"}}
- For temperature/sensor queries: USE_TOOL:ha_get_device_state:{{"domain": "sensor", "name_filter": "LOCATION"}}
- For light control: USE_TOOL:ha_control_light:{{"action": "turn_on|turn_off|toggle", "name_filter": "ROOM"}}
- For switch control: USE_TOOL:ha_control_switch:{{"action": "turn_on|turn_off|toggle", "name_filter": "DEVICE"}}
- Otherwise, provide a helpful conversational response

Your response:"""

class ChatService:
    """Main service that orchestrates LLM and tool interactions."""
    
    def __init__(self):
        self.mcp_client = MCPClient(MCP_SERVER_URL)
        self.ollama_client = OllamaClient(OLLAMA_URL, OLLAMA_MODEL)
        self.available_tools = []
    
    async def initialize(self):
        """Initialize the service by fetching available tools."""
        self.available_tools = await self.mcp_client.get_available_tools()
        logger.info(f"Loaded {len(self.available_tools)} tools from MCP server")
    
    async def _log_interaction(self, log: InteractionLog):
        """Log interaction to Redis."""
        if not redis_client:
            return
        
        try:
            # Store with 24-hour expiration
            key = f"interaction:{log.session_id}:{log.interaction_id}"
            await redis_client.setex(
                key,
                86400,  # 24 hours
                json.dumps(log.dict())
            )
            
            # Also add to session index
            session_key = f"interactions:{log.session_id}"
            await redis_client.lpush(session_key, log.interaction_id)
            await redis_client.expire(session_key, 86400)
            
            logger.info(f"Logged interaction {log.interaction_id}")
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")
    
    async def process_message(self, message: str, session_id: str) -> ChatResponse:
        """Process a user message and return a response."""
        # Generate unique interaction ID
        interaction_id = hashlib.md5(f"{session_id}:{message}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        timestamp = datetime.now().isoformat()
        
        tools_used = []
        llm_payload = None
        llm_response = None
        tool_results = None
        final_response = ""
        
        # Check for direct tool usage patterns first
        tool_response = await self._check_direct_tool_usage(message, session_id)
        if tool_response:
            final_response = tool_response["response"]
            tools_used = tool_response["tools_used"]
            tool_results = tool_response.get("tool_results")
            
            # Create debug info
            debug_info = {
                "routing": "direct_shortcut",
                "explanation": "⚡ Direct routing bypassed the LLM entirely",
                "user_message": message,
                "pattern_matched": tool_response.get("pattern_matched", "unknown"),
                "keywords_detected": tool_response.get("keywords_detected", []),
                "extracted_params": tool_response.get("extracted_params", {}),
                "tool_call": {
                    "tool_name": tools_used[0] if tools_used else None,
                    "arguments": tool_response.get("tool_arguments", {})
                },
                "tools_used": tools_used,
                "tool_results": tool_results,
                "why_no_llm": "Client detected common pattern and called tool directly for speed"
            }
            
            # Log the interaction
            await self._log_interaction(InteractionLog(
                interaction_id=interaction_id,
                session_id=session_id,
                timestamp=timestamp,
                user_message=message,
                llm_payload=None,  # Direct routing, no LLM
                llm_response=None,
                tools_used=tools_used,
                tool_results=tool_results,
                final_response=final_response
            ))
            
            return ChatResponse(
                response=final_response,
                tools_used=tools_used,
                session_id=session_id,
                timestamp=timestamp,
                interaction_id=interaction_id,
                debug=debug_info
            )
        
        # Otherwise, get response from Ollama
        llm_details = await self.ollama_client.generate_with_details(message)
        llm_response = llm_details["response"]
        full_prompt = llm_details["full_prompt"]
        logger.info(f"Initial LLM response: {llm_response}")
        
        # Check if Ollama wants to use a tool
        if "USE_TOOL:" in llm_response:
            tool_response = await self._handle_tool_usage(llm_response, session_id)
            if tool_response:
                tools_used = tool_response["tools_used"]
                tool_results = tool_response.get("results")
                
                # Generate final response with tool results
                tools_context = f"Tool Results: {json.dumps(tool_results, indent=2)}"
                final_details = await self.ollama_client.generate_with_details(message, tools_context)
                final_response = final_details["response"]
                final_prompt = final_details["full_prompt"]
                
                # Create debug info
                debug_info = {
                    "routing": "llm_with_tools",
                    "user_message": message,
                    "initial_prompt": full_prompt,
                    "initial_llm_response": llm_response,
                    "tools_used": tools_used,
                    "tool_results": tool_results,
                    "final_prompt": final_prompt,
                    "final_llm_response": final_response,
                    "model": OLLAMA_MODEL
                }
                
                # Log the interaction
                await self._log_interaction(InteractionLog(
                    interaction_id=interaction_id,
                    session_id=session_id,
                    timestamp=timestamp,
                    user_message=message,
                    llm_payload={"initial_prompt": full_prompt, "final_prompt": final_prompt},
                    llm_response=f"Initial: {llm_response}\nFinal: {final_response}",
                    tools_used=tools_used,
                    tool_results=tool_results,
                    final_response=final_response
                ))
                
                return ChatResponse(
                    response=final_response,
                    tools_used=tools_used,
                    session_id=session_id,
                    timestamp=timestamp,
                    interaction_id=interaction_id,
                    debug=debug_info
                )
        
        final_response = llm_response
        
        # Create debug info for pure conversation
        debug_info = {
            "routing": "llm_only",
            "user_message": message,
            "prompt": full_prompt,
            "llm_response": llm_response,
            "model": OLLAMA_MODEL
        }
        
        # Log the interaction
        await self._log_interaction(InteractionLog(
            interaction_id=interaction_id,
            session_id=session_id,
            timestamp=timestamp,
            user_message=message,
            llm_payload={"prompt": full_prompt},
            llm_response=llm_response,
            tools_used=tools_used,
            tool_results=tool_results,
            final_response=final_response
        ))
        
        return ChatResponse(
            response=final_response,
            tools_used=tools_used,
            session_id=session_id,
            timestamp=timestamp,
            interaction_id=interaction_id,
            debug=debug_info
        )
    
    async def _check_direct_tool_usage(self, message: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Check if the message should directly trigger a tool without LLM processing."""
        logger.info(f"Checking direct tool usage for message: '{message}'")
        
        message_lower = message.lower()
        logger.info(f"Message lowercase: '{message_lower}'")
        
        # Check for time-related questions
        time_keywords = ["time", "date", "current time", "what time", "when is it", "ntp"]
        
        detected_time_keywords = [kw for kw in time_keywords if kw in message_lower]
        
        if detected_time_keywords:
            logger.info(f"Found time keyword(s): {detected_time_keywords} - triggering get_network_time tool")
            result = await self.mcp_client.call_tool("get_network_time", {}, session_id)
            if result["status"] == "success":
                time_data = result["result_data"]
                response_text = f"The current time according to NTP server ({time_data.get('source', 'unknown source')}) is: {time_data.get('readable_time', 'unknown time')}"
                return {
                    "response": response_text, 
                    "tools_used": ["get_network_time"],
                    "tool_results": {"get_network_time": result},
                    "pattern_matched": "time_query",
                    "keywords_detected": detected_time_keywords,
                    "extracted_params": {
                        "query_type": "current_time"
                    },
                    "tool_arguments": {}
                }
        
        # Check for light control
        light_keywords = ["light", "lights", "lamp", "brightness", "dim", "bright"]
        light_actions = {"turn on": "turn_on", "on": "turn_on", "turn off": "turn_off", "off": "turn_off", "toggle": "toggle"}
        
        detected_keywords = [kw for kw in light_keywords if kw in message_lower]
        
        if detected_keywords:
            action = None
            action_phrase = None
            for phrase, act in light_actions.items():
                if phrase in message_lower:
                    action = act
                    action_phrase = phrase
                    break
            
            if action:
                logger.info(f"Found light control: action={action}")
                # Extract room/location or specific light name
                name_filter = None
                
                # Try to extract the target from the message
                # Remove action words first
                clean_message = message_lower
                for phrase in ["turn on", "turn off", "toggle", "the"]:
                    clean_message = clean_message.replace(phrase, "")
                clean_message = clean_message.replace("lights", "").replace("light", "").strip()
                
                if clean_message:
                    name_filter = clean_message
                
                tool_arguments = {"action": action, "name_filter": name_filter}
                
                result = await self.mcp_client.call_tool(
                    "ha_control_light",
                    tool_arguments,
                    session_id
                )
                if result["status"] == "success":
                    data = result["result_data"]
                    
                    # Handle multiple lights
                    if "lights" in data:
                        lights = data["lights"]
                        if data["count"] == 1:
                            light = lights[0]
                            name = light.get('friendly_name', light.get('entity_id', 'light'))
                            state = light.get('new_state', 'unknown')
                            return {
                                "response": f"✓ {name} is now {state}",
                                "tools_used": ["ha_control_light"],
                                "tool_results": {"ha_control_light": result},
                                "pattern_matched": "light_control",
                                "keywords_detected": detected_keywords,
                                "extracted_params": {
                                    "action_phrase": action_phrase,
                                    "action": action,
                                    "target_name": name_filter or "(all matching)"
                                },
                                "tool_arguments": tool_arguments
                            }
                        else:
                            # Multiple lights controlled
                            response_parts = [f"✓ Controlled {data['count']} light(s):"]
                            for light in lights:
                                name = light.get('friendly_name', light.get('entity_id', 'light'))
                                state = light.get('new_state', 'unknown')
                                response_parts.append(f"  • {name}: {state}")
                            return {
                                "response": "\n".join(response_parts),
                                "tools_used": ["ha_control_light"],
                                "tool_results": {"ha_control_light": result},
                                "pattern_matched": "light_control",
                                "keywords_detected": detected_keywords,
                                "extracted_params": {
                                    "action_phrase": action_phrase,
                                    "action": action,
                                    "target_name": name_filter or "(all matching)"
                                },
                                "tool_arguments": tool_arguments
                            }
                    else:
                        # Legacy single light response
                        name = data.get('friendly_name', data.get('entity_id', 'light'))
                        state = data.get('new_state', 'unknown')
                        return {
                            "response": f"✓ {name} is now {state}",
                            "tools_used": ["ha_control_light"],
                            "tool_results": {"ha_control_light": result},
                            "pattern_matched": "light_control",
                            "keywords_detected": detected_keywords,
                            "extracted_params": {
                                "action_phrase": action_phrase,
                                "action": action,
                                "target_name": name_filter or "(all matching)"
                            },
                            "tool_arguments": tool_arguments
                        }
        
        # Check for switch control
        switch_keywords = ["switch", "outlet", "plug", "fan", "coffee"]
        
        detected_switch_keywords = [kw for kw in switch_keywords if kw in message_lower]
        
        if detected_switch_keywords:
            action = None
            action_phrase = None
            for phrase, act in light_actions.items():  # Same actions as lights
                if phrase in message_lower:
                    action = act
                    action_phrase = phrase
                    break
            
            if action:
                logger.info(f"Found switch control: action={action}")
                # Extract device name or area
                name_filter = None
                
                # Remove action words first
                clean_message = message_lower
                for phrase in ["turn on", "turn off", "toggle", "the"]:
                    clean_message = clean_message.replace(phrase, "")
                clean_message = clean_message.replace("switches", "").replace("switch", "").strip()
                
                if clean_message:
                    name_filter = clean_message
                
                tool_arguments = {"action": action, "name_filter": name_filter}
                
                result = await self.mcp_client.call_tool(
                    "ha_control_switch",
                    tool_arguments,
                    session_id
                )
                if result["status"] == "success":
                    data = result["result_data"]
                    
                    # Handle multiple switches
                    if "switches" in data:
                        switches = data["switches"]
                        if data["count"] == 1:
                            switch = switches[0]
                            name = switch.get('friendly_name', switch.get('entity_id', 'switch'))
                            state = switch.get('new_state', 'unknown')
                            return {
                                "response": f"✓ {name} is now {state}",
                                "tools_used": ["ha_control_switch"],
                                "tool_results": {"ha_control_switch": result},
                                "pattern_matched": "switch_control",
                                "keywords_detected": detected_switch_keywords,
                                "extracted_params": {
                                    "action_phrase": action_phrase,
                                    "action": action,
                                    "target_name": name_filter or "(all matching)"
                                },
                                "tool_arguments": tool_arguments
                            }
                        else:
                            # Multiple switches controlled
                            response_parts = [f"✓ Controlled {data['count']} switch(es):"]
                            for switch in switches:
                                name = switch.get('friendly_name', switch.get('entity_id', 'switch'))
                                state = switch.get('new_state', 'unknown')
                                response_parts.append(f"  • {name}: {state}")
                            return {
                                "response": "\n".join(response_parts),
                                "tools_used": ["ha_control_switch"],
                                "tool_results": {"ha_control_switch": result},
                                "pattern_matched": "switch_control",
                                "keywords_detected": detected_switch_keywords,
                                "extracted_params": {
                                    "action_phrase": action_phrase,
                                    "action": action,
                                    "target_name": name_filter or "(all matching)"
                                },
                                "tool_arguments": tool_arguments
                            }
                    else:
                        # Legacy single switch response
                        name = data.get('friendly_name', data.get('entity_id', 'switch'))
                        state = data.get('new_state', 'unknown')
                        return {
                            "response": f"✓ {name} is now {state}",
                            "tools_used": ["ha_control_switch"],
                            "tool_results": {"ha_control_switch": result}
                        }
        
        # Check for ping/connectivity questions
        ping_keywords = ["ping", "connectivity", "connect", "reach", "test"]
        
        detected_ping_keywords = [kw for kw in ping_keywords if kw in message_lower]
        
        if detected_ping_keywords:
            # Try to extract hostname from the message
            words = message.split()
            hostname = "google.com"  # default
            extracted_hostname = None
            for word in words:
                if "." in word and not word.startswith("http") and len(word) > 3:
                    hostname = word.strip(".,!?")
                    extracted_hostname = word
                    break
            
            tool_arguments = {"hostname": hostname}
            
            result = await self.mcp_client.call_tool("ping_host", tool_arguments, session_id)
            if result["status"] == "success":
                ping_data = result["result_data"]
                response_text = f"Ping test to {hostname}: {ping_data.get('status', 'unknown status')}. "
                if ping_data.get('packet_loss_percent', 0) == 0:
                    response_text += f"Connection successful with {ping_data.get('average_latency_ms', 'unknown')} ms average latency."
                else:
                    response_text += f"{ping_data.get('packet_loss_percent', 'unknown')}% packet loss detected."
                return {
                    "response": response_text,
                    "tools_used": ["ping_host"],
                    "tool_results": {"ping_host": result},
                    "pattern_matched": "ping_query",
                    "keywords_detected": detected_ping_keywords,
                    "extracted_params": {
                        "hostname": hostname,
                        "extracted_from_message": extracted_hostname or "(default: google.com)"
                    },
                    "tool_arguments": tool_arguments
                }
        
        return None
    
    async def _handle_tool_usage(self, llm_response: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Parse and execute tool usage from LLM response."""
        try:
            # Parse tool usage from response
            # Format: USE_TOOL:tool_name:{"arg1": "value1"}
            if "USE_TOOL:" not in llm_response:
                return None
            
            # Extract the tool call line
            lines = llm_response.split("\n")
            tool_line = None
            for line in lines:
                if "USE_TOOL:" in line:
                    tool_line = line.strip()
                    break
            
            if not tool_line:
                return None
            
            # Parse the tool call
            tool_part = tool_line.split("USE_TOOL:")[1]
            
            # Handle different formats the LLM might use
            if ":" in tool_part:
                parts = tool_part.split(":", 1)
                tool_name = parts[0].strip()
                arguments_str = parts[1].strip()
                
                # Try to parse JSON arguments
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError:
                    # If JSON parsing fails, assume empty arguments for tools like get_network_time
                    if arguments_str in ["{}", "{timestamp}"] or not arguments_str:
                        arguments = {}
                    else:
                        # Try to extract hostname from simple format
                        if "hostname" in arguments_str:
                            hostname_match = arguments_str.split('"')
                            if len(hostname_match) >= 2:
                                arguments = {"hostname": hostname_match[1]}
                            else:
                                arguments = {}
                        else:
                            arguments = {}
            else:
                tool_name = tool_part.strip()
                arguments = {}
            
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
            
            # Execute the tool
            result = await self.mcp_client.call_tool(tool_name, arguments, session_id)
            
            return {
                "tools_used": [tool_name],
                "results": {tool_name: result}
            }
            
        except Exception as e:
            logger.error(f"Failed to handle tool usage: {e}")
            return None

# Initialize the chat service
chat_service = ChatService()

async def init_mysql_pool():
    """Initialize MySQL connection pool."""
    global mysql_pool
    if not MYSQL_AVAILABLE:
        logger.warning("MySQL library (aiomysql) not available - feedback will only be stored in Redis")
        return
    
    if not MYSQL_PASSWORD:
        logger.warning("MYSQL_PASSWORD not set - skipping MySQL initialization")
        return
    
    try:
        mysql_pool = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            charset='utf8mb4',
            minsize=1,
            maxsize=MYSQL_POOL_SIZE,
            autocommit=True
        )
        logger.info(f"MySQL connection pool initialized: {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
    except Exception as e:
        logger.error(f"Failed to initialize MySQL pool: {e}")
        mysql_pool = None

async def close_mysql_pool():
    """Close MySQL connection pool."""
    global mysql_pool
    if mysql_pool:
        mysql_pool.close()
        await mysql_pool.wait_closed()
        logger.info("MySQL connection pool closed")

async def save_interaction_to_mysql(log: InteractionLog):
    """Save thumbs-up interaction to MySQL for permanent storage."""
    if not mysql_pool:
        return
    
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = """
                INSERT INTO interactions 
                (interaction_id, session_id, user_message, final_response, routing_type, 
                 model, tools_used, tool_results, llm_payload, llm_response, debug_info, feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    feedback = VALUES(feedback),
                    updated_at = CURRENT_TIMESTAMP
                """
                
                # Determine routing type from debug info or tools used
                routing_type = "llm_only"
                if log.tools_used:
                    routing_type = "llm_with_tools" if log.llm_payload else "direct_shortcut"
                
                await cursor.execute(query, (
                    log.interaction_id,
                    log.session_id,
                    log.user_message,
                    log.final_response,
                    routing_type,
                    None,  # model - will extract from debug if needed
                    json.dumps(log.tools_used) if log.tools_used else None,
                    json.dumps(log.tool_results) if log.tool_results else None,
                    json.dumps(log.llm_payload) if log.llm_payload else None,
                    log.llm_response,
                    None,  # debug_info - can add if needed
                    log.feedback or 'thumbs_up'
                ))
                
                logger.info(f"Saved interaction {log.interaction_id} to MySQL")
    except Exception as e:
        logger.error(f"Failed to save interaction to MySQL: {e}")

async def save_negative_feedback_to_mysql(interaction_id: str, session_id: str, log_data: dict):
    """Save thumbs-down feedback to MySQL for analysis."""
    if not mysql_pool:
        return
    
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = """
                INSERT INTO negative_feedback 
                (interaction_id, session_id, user_message, final_response, routing_type, 
                 model, tools_used, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                # Determine routing type
                routing_type = "llm_only"
                tools_used = log_data.get('tools_used', [])
                if tools_used:
                    routing_type = "llm_with_tools" if log_data.get('llm_payload') else "direct_shortcut"
                
                await cursor.execute(query, (
                    interaction_id,
                    session_id,
                    log_data.get('user_message', ''),
                    log_data.get('final_response', ''),
                    routing_type,
                    None,  # model
                    json.dumps(tools_used) if tools_used else None,
                    "User gave thumbs down"
                ))
                
                logger.info(f"Saved negative feedback {interaction_id} to MySQL")
    except Exception as e:
        logger.error(f"Failed to save negative feedback to MySQL: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize the chat service on startup."""
    await chat_service.initialize()
    await init_mysql_pool()
    logger.info(f"MCP Client started on port {CLIENT_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await close_mysql_pool()
    logger.info("MCP Client shutdown complete")

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if we can reach both Ollama and MCP server
    ollama_status = "unknown"
    mcp_status = "unknown"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check Ollama
            try:
                ollama_response = await client.get(f"{OLLAMA_URL}/api/tags")
                ollama_status = "connected" if ollama_response.status_code == 200 else "error"
            except:
                ollama_status = "disconnected"
            
            # Check MCP server
            try:
                mcp_response = await client.get(f"{MCP_SERVER_URL}/health")
                mcp_status = "connected" if mcp_response.status_code == 200 else "error"
            except:
                mcp_status = "disconnected"
    except:
        pass
    
    return {
        "status": "ok",
        "service": "mcp-client",
        "ollama": ollama_status,
        "mcp_server": mcp_status,
        "model": OLLAMA_MODEL
    }

@app.get("/tools")
async def list_tools():
    """List available MCP tools."""
    return [tool.dict() for tool in chat_service.available_tools]

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint."""
    try:
        response = await chat_service.process_message(request.message, request.session_id)
        return response
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

class TestToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to test")
    arguments: Dict[str, Any] = Field(default={}, description="Tool arguments")

@app.post("/test-tool")
async def test_tool_endpoint(request: TestToolRequest):
    """Direct tool testing endpoint."""
    result = await chat_service.mcp_client.call_tool(request.tool_name, request.arguments, "test-session")
    return result

@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "service": "MCP Client - Ollama Integration", 
        "version": "1.0.0",
        "ollama_model": OLLAMA_MODEL,
        "mcp_server": MCP_SERVER_URL,
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health", 
            "tools": "GET /tools",
            "test-tool": "POST /test-tool",
            "interaction": "GET /interaction/{session_id}/{interaction_id}",
            "feedback": "POST /feedback"
        }
    }

@app.get("/interaction/{session_id}/{interaction_id}")
async def get_interaction_log(session_id: str, interaction_id: str):
    """Retrieve interaction log details."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available for logging")
    
    try:
        key = f"interaction:{session_id}:{interaction_id}"
        data = await redis_client.get(key)
        
        if not data:
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        return json.loads(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve interaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve interaction: {str(e)}")

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback (thumbs up/down) for an interaction."""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available for feedback")
    
    if request.feedback not in ["thumbs_up", "thumbs_down"]:
        raise HTTPException(status_code=400, detail="Feedback must be 'thumbs_up' or 'thumbs_down'")
    
    try:
        key = f"interaction:{request.session_id}:{request.interaction_id}"
        data = await redis_client.get(key)
        
        if not data:
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        # Parse existing log
        log_data = json.loads(data)
        log_data['feedback'] = request.feedback
        
        if request.feedback == "thumbs_up":
            # Thumbs up: make it permanent (no expiration in Redis)
            await redis_client.set(key, json.dumps(log_data))
            
            # Add to permanent feedback index
            feedback_key = f"feedback:thumbs_up:{request.session_id}"
            await redis_client.sadd(feedback_key, request.interaction_id)
            
            # Save to MySQL for permanent storage
            interaction_log = InteractionLog(**log_data)
            await save_interaction_to_mysql(interaction_log)
            
            logger.info(f"👍 Interaction {request.interaction_id} marked as thumbs_up (permanent)")
            return {"status": "success", "message": "Feedback recorded. This interaction will be kept permanently."}
            
        elif request.feedback == "thumbs_down":
            # Save negative feedback to MySQL for analysis before deleting
            await save_negative_feedback_to_mysql(request.interaction_id, request.session_id, log_data)
            
            # Thumbs down: delete from Redis immediately
            await redis_client.delete(key)
            
            # Add to negative feedback index (with expiration)
            feedback_key = f"feedback:thumbs_down:{request.session_id}"
            await redis_client.sadd(feedback_key, request.interaction_id)
            await redis_client.expire(feedback_key, 86400)  # Keep negative feedback for 24h for analysis
            
            logger.info(f"👎 Interaction {request.interaction_id} marked as thumbs_down (deleted)")
            return {"status": "success", "message": "Feedback recorded. This interaction has been removed."}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")