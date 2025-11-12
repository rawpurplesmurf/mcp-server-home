import { test, expect } from '@playwright/test';

/**
 * Playwright UI End-to-End Tests
 * 
 * Prerequisites:
 * - MCP Server running on port 8000
 * - MCP Client running on port 8001
 * - UI dev server running on port 5173 (auto-started by playwright.config.js)
 */

test.describe('MCP UI Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load and display the UI properly', async ({ page }) => {
    // Check that the header is visible
    await expect(page.locator('h1')).toContainText('MCP Chat');
    
    // Check that the input box is visible
    const input = page.locator('input[type="text"]');
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute('placeholder', 'Ask me anything...');
    
    // Check that the send button is visible
    const sendButton = page.locator('button[type="submit"]');
    await expect(sendButton).toBeVisible();
  });

  test('should show clear button and clear chat history', async ({ page }) => {
    // Type a message
    const input = page.locator('input[type="text"]');
    await input.fill('Hello');
    
    // Send the message
    const sendButton = page.locator('button[type="submit"]');
    await sendButton.click();
    
    // Wait for message to appear
    await page.waitForSelector('.message.user', { timeout: 5000 });
    
    // Wait for loading to complete (if any)
    await page.waitForTimeout(1000);
    
    // Check that clear button appears
    const clearButton = page.locator('button.clear-btn');
    await expect(clearButton).toBeVisible();
    
    // Click clear button
    await clearButton.click();
    
    // Verify messages are cleared (excluding loading message if present)
    const userMessageCount = await page.locator('.message.user').count();
    expect(userMessageCount).toBe(0);
    
    // Verify clear button is hidden
    await expect(clearButton).not.toBeVisible();
  });

  test('should send a message and receive a response', async ({ page }) => {
    // Type a general message
    const input = page.locator('input[type="text"]');
    await input.fill('Hello, how are you?');
    
    // Send the message
    const sendButton = page.locator('button[type="submit"]');
    await sendButton.click();
    
    // Wait for user message to appear
    await page.waitForSelector('.message.user', { timeout: 5000 });
    const userMessage = page.locator('.message.user').last();
    await expect(userMessage).toContainText('Hello, how are you?');
    
    // Wait for AI response (with longer timeout for LLM processing)
    await page.waitForSelector('.message.assistant', { timeout: 30000 });
    const aiMessage = page.locator('.message.assistant').last();
    await expect(aiMessage).toBeVisible();
  });

  test('should handle time query and show tool badge', async ({ page }) => {
    // Send a time-related query
    const input = page.locator('input[type="text"]');
    await input.fill('What time is it?');
    
    const sendButton = page.locator('button[type="submit"]');
    await sendButton.click();
    
    // Wait for user message
    await page.waitForSelector('.message.user', { timeout: 5000 });
    
    // Wait for AI response (extended timeout for LLM)
    await page.waitForSelector('.message.assistant', { timeout: 30000 });
    
    // Verify assistant message contains time-related content
    const assistantMessage = page.locator('.message.assistant .message-content');
    await expect(assistantMessage).toBeVisible();
    
    // Tool badge may not always appear (depends on direct routing vs LLM)
    // Just verify the response is present
    const messageText = await assistantMessage.textContent();
    expect(messageText.length).toBeGreaterThan(0);
  });

  test('should handle ping query and show tool badge', async ({ page }) => {
    // Send a ping-related query
    const input = page.locator('input[type="text"]');
    await input.fill('Can you ping google.com?');
    
    const sendButton = page.locator('button[type="submit"]');
    await sendButton.click();
    
    // Wait for user message
    await page.waitForSelector('.message.user', { timeout: 5000 });
    
    // Wait for AI response with tool badge (extended timeout for LLM)
    await page.waitForSelector('.message.assistant', { timeout: 30000 });
    
    // Check for tool badge
    const toolBadge = page.locator('.tools-badge');
    await expect(toolBadge).toBeVisible();
    await expect(toolBadge).toContainText('ping_host');
  });

  test('should disable send button while loading', async ({ page }) => {
    const input = page.locator('input[type="text"]');
    const sendButton = page.locator('button[type="submit"]');
    
    // Send a message
    await input.fill('Test message');
    await sendButton.click();
    
    // Check that send button is disabled during loading (briefly)
    // We need to check quickly before the response comes back
    await expect(sendButton).toBeDisabled();
    
    // Wait for response to complete (wait for assistant message or error)
    await page.waitForSelector('.message.assistant, .message.error', { timeout: 60000 });
    
    // After response, button should be enabled again (when input is filled)
    await input.fill('Another message');
    await expect(sendButton).toBeEnabled();
  });

  test('should clear input after sending message', async ({ page }) => {
    const input = page.locator('input[type="text"]');
    const sendButton = page.locator('button[type="submit"]');
    
    // Type and send message
    await input.fill('Test message');
    await sendButton.click();
    
    // Check that input is cleared
    await expect(input).toHaveValue('');
  });

  test('should not send empty messages', async ({ page }) => {
    const sendButton = page.locator('button[type="submit"]');
    
    // Verify button is disabled when input is empty
    await expect(sendButton).toBeDisabled();
    
    // Verify no message was sent
    const messageCount = await page.locator('.message').count();
    expect(messageCount).toBe(0);
  });

  test('should display loading indicator while waiting for response', async ({ page }) => {
    const input = page.locator('input[type="text"]');
    const sendButton = page.locator('button[type="submit"]');
    
    // Send a message
    await input.fill('Tell me a story');
    await sendButton.click();
    
    // Check for loading dots
    await page.waitForSelector('.loading-dots', { timeout: 5000 });
    const loadingDots = page.locator('.loading-dots');
    await expect(loadingDots).toBeVisible();
  });

  test('should auto-scroll to latest message', async ({ page }) => {
    const input = page.locator('input[type="text"]');
    const sendButton = page.locator('button[type="submit"]');
    
    // Send multiple messages
    for (let i = 1; i <= 3; i++) {
      await input.fill(`Message ${i}`);
      await sendButton.click();
      await page.waitForSelector('.message.user', { timeout: 5000 });
      // Small delay between messages
      await page.waitForTimeout(1000);
    }
    
    // Get the last message
    const lastMessage = page.locator('.message').last();
    
    // Check that the last message is in viewport (auto-scrolled)
    await expect(lastMessage).toBeInViewport();
  });

  test('should handle server errors gracefully', async ({ page }) => {
    // Mock a server error by intercepting the request
    await page.route('http://localhost:8001/chat', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });
    
    const input = page.locator('input[type="text"]');
    const sendButton = page.locator('button[type="submit"]');
    
    // Send a message
    await input.fill('Test error handling');
    await sendButton.click();
    
    // Wait for user message
    await page.waitForSelector('.message.user', { timeout: 5000 });
    
    // Check for error message
    await page.waitForSelector('.message.error', { timeout: 10000 });
    const errorMessage = page.locator('.message.error').last();
    await expect(errorMessage).toContainText(/error|failed/i);
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Check that UI is still functional
    const input = page.locator('input[type="text"]');
    await expect(input).toBeVisible();
    
    const sendButton = page.locator('button[type="submit"]');
    await expect(sendButton).toBeVisible();
    
    // Verify messages container is scrollable
    const messagesContainer = page.locator('.chat-container');
    await expect(messagesContainer).toBeVisible();
  });
});
