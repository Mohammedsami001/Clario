# Fully automated, asynchronous video processing

Processing a long-form Source Video into short-form segments takes significant time and happens entirely in the background. We decided not to include a "human in the loop" review step (e.g. asking the Learner to approve timestamps or segments) because the Learner typically hasn't watched the video yet and wouldn't know what to approve. 

The AI must act autonomously to extract the segments, and the backend must handle this as an asynchronous background job without blocking the UI or requiring the user to stay online.
