#!/usr/bin/env python
import asyncio
from typing import List
# Import it into your project
from datetime import datetime


from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from write_a_book_with_flows.crews.write_book_chapter_crew.write_book_chapter_crew import (
    WriteBookChapterCrew,
)
from write_a_book_with_flows.types import Chapter, ChapterOutline

from .crews.outline_book_crew.outline_crew import OutlineCrew

# from langtrace_python_sdk import langtrace # Must precede any llm module imports
# langtrace.init(api_key = '0506b0299c82eac2f01a18587c6a5f02adfd49a963da89b221e2a16547f6aac9')

# from pydantic import BaseModel
# from typing import List
#
# class ChapterOutline(BaseModel):
#     title: str
#     description: str
#
# class BookOutline(BaseModel):
#     chapters: List[ChapterOutline]

class BookState(BaseModel):
    title: str = (
        "The Current State of AI in September 2024 - Trends Across Industries"
    )
    book: List[Chapter] = []
    book_outline: List[ChapterOutline] = []
    topic: str = (
        "Exploring the latest trends in AI across different industries as of September 2024"
    )
    goal: str = """
        The goal of this book is to provide a comprehensive overview of the current state of artificial intelligence in September 2024.
        It will delve into the latest trends impacting various industries, analyze significant advancements,
        and discuss potential future developments. The book aims to inform readers about cutting-edge AI technologies
        and prepare them for upcoming innovations in the field.
    """


class BookFlow(Flow[BookState]):

    @start()
    def generate_book_outline(self):
        print("Kickoff the Book Outline Crew")
        output = (
            OutlineCrew()
            .crew()
            .kickoff(inputs={"topic": self.state.topic, "goal": self.state.goal})
        )

        chapters = output["chapters"]

        print(f"This is all the Chapters:", chapters)

        self.state.book_outline = chapters

    @listen(generate_book_outline)
    async def write_chapters(self):
        print("Writing Book Chapters")
        tasks = []

        async def write_single_chapter(chapter_outline):
            output = (
                WriteBookChapterCrew()
                .crew()
                .kickoff(
                    inputs={
                        "goal": self.state.goal,
                        "topic": self.state.topic,
                        "chapter_title": chapter_outline.title,
                        "chapter_description": chapter_outline.description,
                        "book_outline": [
                            chapter_outline.model_dump_json()
                            for chapter_outline in self.state.book_outline
                        ],
                    }
                )
            )
            title = output["title"]
            content = output["content"]
            chapter = Chapter(title=title, content=content)
            return chapter

        for chapter_outline in self.state.book_outline:
            print(f"Writing Chapter: {chapter_outline.title}")
            print(f"Description: {chapter_outline.description}")
            # Schedule each chapter writing task
            task = asyncio.create_task(write_single_chapter(chapter_outline))
            tasks.append(task)

        # Await all chapter writing tasks concurrently
        chapters = await asyncio.gather(*tasks)
        print("Newly generated chapters:", chapters)
        self.state.book.extend(chapters)

        print("Book Chapters", self.state.book)

    @listen(write_chapters)
    async def join_and_save_chapter(self):
        print("Joining and Saving Book Chapters")
        # Combine all chapters into a single markdown string
        book_content = ""

        for chapter in self.state.book:
            # Add the chapter title as an H1 heading
            book_content += f"# {chapter.title}\n\n"
            # Add the chapter content
            book_content += f"{chapter.content}\n\n"

        # The title of the book from self.state.title
        book_title = self.state.title

        # Create the filename by replacing spaces with underscores and adding .md extension
        # filename = f"./{book_title.replace(' ', '_')}_{}.md"
        # filename = filename.format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        # Save the combined content into the file
        # Get the current date and time
        current_datetime = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        # Generate the filename with all components combined using underscores
        filename = f"./{book_title.replace(' ', '_')}_{current_datetime}.md"

        with open(filename, "w", encoding="utf-8") as file:
            file.write(book_content)

        print(f"Book saved as {filename}")


def kickoff():
    poem_flow = BookFlow()
    poem_flow.kickoff()


def plot():
    poem_flow = BookFlow()
    poem_flow.plot()


if __name__ == "__main__":
    kickoff()
