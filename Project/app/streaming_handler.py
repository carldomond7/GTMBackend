# Project/app/streaming_handler.py
import asyncio


class StreamingHandler:
    def __init__(self, chunk_size: int):
        self.chunk_size = chunk_size

    async def create_generator(self, input_text: str):
        # Generate results from the query processor
        result = input_text

        # Check if result is a string
        if isinstance(result, str):
            # Split the result into separate substrings based on chunk_size
            chunks = [result[i:i+self.chunk_size] for i in range(0, len(result), self.chunk_size)]
        else:
            # If result is not a string, convert it to a string representation
            result_str = str(result)
            # Split the result_str into separate substrings based on chunk_size
            chunks = [result_str[i:i+self.chunk_size] for i in range(0, len(result_str), self.chunk_size)]

        # Iterate through each substring entry and yield chunk to user
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.1)  # Implement a small delay between chunks
