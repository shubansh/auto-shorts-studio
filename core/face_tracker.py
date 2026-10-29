import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FaceTracker:
    def __init__(self):
        # OpenCV built-in Haar Cascade for ultra-fast, zero-dependency offline face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            logger.warning("Could not load OpenCV default face cascade.")

    def calculate_crop_window(self, video_path: str, start_time: float, end_time: float, width: int, height: int) -> dict:
        """
        Samples video frames across the clip duration to find the speaker's face.
        Calculates an optimal, smoothed 9:16 crop window (X offset).
        Returns crop dictionary: {"crop_w": int, "crop_h": int, "crop_x": int, "crop_y": 0}
        """
        # Desired 9:16 crop dimensions matching input height
        crop_h = height
        crop_w = int(height * 9 / 16)
        # Ensure crop width is an even number for H.264 codecs
        if crop_w % 2 != 0:
            crop_w += 1

        # If original video is already vertical (e.g. 9:16)
        if width <= crop_w:
            return {"crop_w": width, "crop_h": height, "crop_x": 0, "crop_y": 0}

        default_x = (width - crop_w) // 2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning(f"Failed to open {video_path} for face tracking, using center crop.")
            return {"crop_w": crop_w, "crop_h": crop_h, "crop_x": default_x, "crop_y": 0}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        total_frames = end_frame - start_frame

        # Sample 1 frame every 0.5s to keep it fast
        sample_step = max(1, int(fps * 0.5))
        face_x_centers = []

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        curr_frame = start_frame

        while curr_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            if (curr_frame - start_frame) % sample_step == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Downscale for 5x faster face detection
                small_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)
                faces = self.face_cascade.detectMultiScale(
                    small_gray,
                    scaleFactor=1.15,
                    minNeighbors=5,
                    minSize=(30, 30)
                )

                if len(faces) > 0:
                    # Pick the largest face (assumed to be the main speaker)
                    largest_face = max(faces, key=lambda f: f[2] * f[3])
                    # Scale back to original dimensions
                    fx, fy, fw, fh = [coord * 2 for coord in largest_face]
                    face_center_x = fx + (fw // 2)
                    face_x_centers.append(face_center_x)

            curr_frame += 1

        cap.release()

        # If faces were detected, compute the robust median center
        if face_x_centers:
            # Use median to ignore occasional false positive outliers
            median_center_x = int(np.median(face_x_centers))
            target_x = median_center_x - (crop_w // 2)
            # Clamp within video boundaries
            target_x = max(0, min(width - crop_w, target_x))
            # Ensure even number
            if target_x % 2 != 0:
                target_x += 1
            logger.info(f"Detected speaker face at median X={median_center_x}, crop_x={target_x}")
            return {"crop_w": crop_w, "crop_h": crop_h, "crop_x": target_x, "crop_y": 0}

        logger.info(f"No face detected in clip, using center crop X={default_x}")
        return {"crop_w": crop_w, "crop_h": crop_h, "crop_x": default_x, "crop_y": 0}
