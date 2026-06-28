from browser_use import Agent, Browser, ChatBrowserUse
import asyncio

async def example():
    browser = Browser(
    )

    llm = ChatBrowserUse()

    agent = Agent(
        task="Find out the best sneakers available for sale in under 3000 INR based on highest reviews and ratings. Provide the links to the products as well.",
        llm=llm,
        browser=browser,
    )

    history = await agent.run()
    return history

if __name__ == "__main__":
    history = asyncio.run(example())