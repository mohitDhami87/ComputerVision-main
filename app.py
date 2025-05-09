import numpy as np
import supervision as sv
from ultralytics import YOLO
from tqdm import tqdm
import cv2

# YOLO V8 models in order from small/quick/less good - large/slow/more good 
# yolov8n - nano
# yolov8s - small
# yolov8m - medium
# yolov8l - large
# yolov8x - extra large

# models will download on first use if not already installed locally

# Load YOLO Model
model = YOLO("./models/yolov8x.pt")

# Define vehicle class IDs (2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck')
selected_classes = [2, 3, 5, 7]

# Define source and target video paths
SOURCE_VIDEO_PATH = "./video/sample2.mp4"
TARGET_VIDEO_PATH = "./video/result2.mp4"

# Create VideoInfo instance
video_info = sv.VideoInfo.from_video_path(SOURCE_VIDEO_PATH)

# Create frame generator
generator = sv.get_video_frames_generator(SOURCE_VIDEO_PATH)

# Create ByteTracker Instance
tracker = sv.ByteTrack(track_activation_threshold=0.25, lost_track_buffer=60, minimum_matching_threshold=0.8, frame_rate=30)

# Create BoxAnnotator Instance
box_annotator = sv.BoundingBoxAnnotator()

# Create DotAnnotator Instance
dot_annotator = sv.DotAnnotator(radius=0)

# Define line zones for counting
LINE_START_ONE = sv.Point(250, 225)
LINE_END_ONE = sv.Point(0, 175)

LINE_START_TWO = sv.Point(375, 225)
LINE_END_TWO = sv.Point(270, 225)

LINE_START_THREE = sv.Point(600, 280)
LINE_END_THREE = sv.Point(425, 230)

# Create LineZone Instances
line_zones = [
    sv.LineZone(start=LINE_START_ONE, end=LINE_END_ONE),
    sv.LineZone(start=LINE_START_TWO, end=LINE_END_TWO),
    sv.LineZone(start=LINE_START_THREE, end=LINE_END_THREE)
]

# Create LineZoneAnnotator instance
line_zone_annotator = sv.LineZoneAnnotator(thickness=1, text_thickness=1)

# Filter detections to only keep vehicles
def filter_vehicle_detections(detections):
    vehicle_detections = detections[np.isin(detections.class_id, selected_classes)]
    return vehicle_detections

# Processes a single video frame to detect, track, and annotate vehicles.    
def callback(frame: np.ndarray, _: int) -> np.ndarray:
    # This function performs the following steps:
    # 1. Model prediction on the input frame to obtain detection results.
    # 2. Converts the detection results into a format suitable for further processing.
    # 3. Filters the detections to retain only vehicles.
    # 4. Updates the tracker with the filtered vehicle detections.
    # 5. Annotates the frame with bounding boxes around detected vehicles.
    # 6. Annotates the frame with dots for line crossing checks.
    # 7. Updates and triggers line counters based on vehicle detections.
    # 8. Annotates the frame with line counters information.

    # Args:
    #     frame (np.ndarray): The input video frame to be processed.
    #     _ (int): A placeholder for an unused parameter.

    # Returns:
    #     np.ndarray: The annotated video frame.

    # Model prediction on single frame and conversion to supervision Detections
    results = model(frame)[0]
    detections = sv.Detections.from_ultralytics(results)
    # Filter only vehicle detections
    detections = filter_vehicle_detections(detections)
    # Update tracker with vehicle detections
    detections = tracker.update_with_detections(detections)

    # Annotate frame with bounding boxes
    annotated_frame = box_annotator.annotate(scene=frame.copy(), detections=detections)
    
    # Annotate frame with dots for line crossing check (dot hidden)
    annotated_frame = dot_annotator.annotate(scene=annotated_frame, detections=detections)

    # Update line counters
    for line_zone in line_zones:
        line_zone.trigger(detections)

    # Annotate frame with line counters
    for line_zone in line_zones:
        annotated_frame = line_zone_annotator.annotate(annotated_frame, line_counter=line_zone)

    return annotated_frame

# Processes a video file frame-by-frame with a progress bar.    
def process_video_with_progress(source_path: str, target_path: str, callback, progress_desc: str = "Processing"):
    # This function performs the following steps:
    # 1. Opens the video file from the specified source path.
    # 2. Calculates the total number of frames in the video.
    # 3. Initializes a progress bar to track the processing progress.
    # 4. Defines a wrapped callback function to process each frame and update the progress bar.
    # 5. Processes the video using the wrapped callback function, saving the result to the target path.

    # Args:
    #     source_path (str): The path to the input video file.
    #     target_path (str): The path to save the processed video file.
    #     callback (function): The function to process each frame. It should take a frame and frame index as arguments and return the processed frame.
    #     progress_desc (str): Description text for the progress bar. Defaults to "Processing".
    
    cap = cv2.VideoCapture(source_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    with tqdm(total=total_frames, desc=progress_desc) as pbar:
        def wrapped_callback(frame: np.ndarray, frame_idx: int) -> np.ndarray:
            result_frame = callback(frame, frame_idx)
            pbar.update(1)
            return result_frame
        
        sv.process_video(
            source_path=source_path,
            target_path=target_path,
            callback=wrapped_callback
        )

# Process the whole video
process_video_with_progress(
    source_path=SOURCE_VIDEO_PATH,
    target_path=TARGET_VIDEO_PATH,
    callback=callback
)