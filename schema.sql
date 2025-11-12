-- MCP Chat Feedback Database Schema
-- This stores permanently approved interactions with thumbs-up feedback

CREATE DATABASE IF NOT EXISTS mcp_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mcp_chat;

-- Main interactions table for approved responses
CREATE TABLE IF NOT EXISTS interactions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    interaction_id VARCHAR(32) NOT NULL UNIQUE,
    session_id VARCHAR(64) NOT NULL,
    user_message TEXT NOT NULL,
    final_response TEXT NOT NULL,
    routing_type ENUM('direct_shortcut', 'llm_with_tools', 'llm_only') NOT NULL,
    model VARCHAR(100),
    tools_used JSON,
    tool_results JSON,
    llm_payload JSON,
    llm_response TEXT,
    debug_info JSON,
    feedback VARCHAR(20) DEFAULT 'thumbs_up',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_routing_type (routing_type),
    INDEX idx_created_at (created_at),
    INDEX idx_feedback (feedback),
    FULLTEXT INDEX idx_user_message (user_message),
    FULLTEXT INDEX idx_final_response (final_response)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Negative feedback tracking (for analysis)
CREATE TABLE IF NOT EXISTS negative_feedback (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    interaction_id VARCHAR(32) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    user_message TEXT NOT NULL,
    final_response TEXT NOT NULL,
    routing_type ENUM('direct_shortcut', 'llm_with_tools', 'llm_only'),
    model VARCHAR(100),
    tools_used JSON,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_routing_type (routing_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Feedback statistics summary
CREATE TABLE IF NOT EXISTS feedback_stats (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_interactions INT DEFAULT 0,
    thumbs_up_count INT DEFAULT 0,
    thumbs_down_count INT DEFAULT 0,
    direct_shortcut_count INT DEFAULT 0,
    llm_with_tools_count INT DEFAULT 0,
    llm_only_count INT DEFAULT 0,
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- View for quick analytics
CREATE OR REPLACE VIEW feedback_summary AS
SELECT 
    routing_type,
    COUNT(*) as total_count,
    AVG(CHAR_LENGTH(user_message)) as avg_message_length,
    AVG(CHAR_LENGTH(final_response)) as avg_response_length,
    DATE(created_at) as date
FROM interactions
GROUP BY routing_type, DATE(created_at)
ORDER BY date DESC, total_count DESC;

-- View for tool usage analysis
CREATE OR REPLACE VIEW tool_usage_stats AS
SELECT 
    JSON_UNQUOTE(JSON_EXTRACT(tools_used, CONCAT('$[', idx, ']'))) as tool_name,
    COUNT(*) as usage_count,
    routing_type
FROM interactions
CROSS JOIN (
    SELECT 0 as idx UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
) as indexes
WHERE JSON_LENGTH(tools_used) > idx
GROUP BY tool_name, routing_type
ORDER BY usage_count DESC;
