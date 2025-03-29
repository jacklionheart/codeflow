import asyncio
from typing import Dict, Any

from loopflow.llm import LLM, LLMProvider
class Team:
    """
    A set of LLMs used to execute jobs.
    """
    
    def __init__(self, providers: Dict[str, LLMProvider], llms: Dict[str, LLM]):
        self.providers = providers
        self.llms = llms

    
    async def query_parallel(self, prompt_template: str, args: Dict[str, Any]) -> Dict[str, str]:
        tasks = []
        mate_names = []
        
        for name, llm in self.llms.items():
            prompt = prompt_template.format(name=name, **args)
            # Create the coroutine but don't await it yet
            tasks.append(asyncio.create_task(llm.chat(prompt)))
            mate_names.append(name)
        
        # Now await all tasks together
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for name, response in zip(mate_names, responses):
            if isinstance(response, Exception):
                results[name] = f"Error: {str(response)}"
            else:
                results[name] = response
        
        return results
    
    def total_cost(self) -> float:
        return sum(provider.usage.total_cost() for provider in self.providers.values())


