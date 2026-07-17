# Clario

An application that transforms long-form videos (like lectures) into concise, scrollable short-form content to save time and aid in revision.

## Language

**Source Video**:
The original, long-form video provided by the user (usually via a link) that needs to be analyzed and broken down.
_Avoid_: Lecture, original video, full video

**Learner**:
The person who interacts with the application to consume or create content.
_Avoid_: User, individual, student

**Project**:
The overarching container that holds a single Source Video, its analysis state, and the resulting short videos. 
_Avoid_: Analysis job, video session, task

**Processing**:
The fully automated background phase where the AI intelligently analyzes the Source Video and breaks it down into short segments.
_Avoid_: Analysis, extraction, magic

**Study Reel**:
A single, short, vertically-scrollable video segment generated from the Source Video. Multiple Study Reels make up the final output for a Project.
_Avoid_: Short, segment, clip
