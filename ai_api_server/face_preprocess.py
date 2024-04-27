import os
from typing import List
import cv2
import torch
import numpy as np
from PIL import Image
from ultralytics import YOLO
import head_segmentation.segmentation_pipeline as seg_pipeline
from dto import Background

class FaceDetector: 
    def __init__(self, model_path):
        self.model = YOLO(model_path, task='detect', verbose=False)
        self.warmup_model(imgsz=640)  

    def warmup_model(self, imgsz=640):
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        dummy_img = torch.zeros((1, 3, imgsz, imgsz), device=device)
        self.model.predict(dummy_img, task='detect', verbose=False)

    def detect(self, images, imgsz=640, max_det=1):
        """
        Args:
            images (List[numpy.ndarray]): A List of images for detecting.
            imgsz (int, optional): Resizing size. Defaults to 640.
            max_det (int, optional): Maximum # of detections per image. Defaults to 1.

        Returns:
            Python generator of Results.
        """
        results = self.model(images, 
                             max_det=max_det, 
                             imgsz=imgsz,
                             verbose=False,
                             )
        return results

    def crop_faces(self, results, image, margin):
        """
        Args:
            results (List[ultralytics.engine.results.Results]): Results returned by "detect" method.
            original_image (List[numpy.ndarray]):  A List of images for cropping. 
            margin (float): A margin value to add around the detected face bbox.

        Returns:
            List[numpy.ndarray]: A list of cropped images containing the detected faces.
        """
        cropped_images = []
        for i, r in enumerate(results):
            for box in r.boxes.xyxy:
                x1, y1, x2, y2 = map(lambda x: int(x.item()), box[:4])
                new_x1, new_y1, new_x2, new_y2 = self.calculate_margins(x1, y1, x2, y2, margin, i, image)
                cropped_img = image[i][new_y1:new_y2, new_x1:new_x2]
                cropped_images.append(cropped_img)
        return cropped_images
    

    def calculate_margins(self, x1, y1, x2, y2, margin, i, image):
        bbox_width = x2 - x1
        bbox_height = y2 - y1
        image_width, image_height = image[i].shape[1], image[i].shape[0]
        new_x1 = max(0, x1 - margin * 0.2 * bbox_width)
        new_y1 = max(0, y1 - margin * 0.3 * bbox_height)
        new_x2 = min(image_width, x2 + margin * 0.2 * bbox_width) 
        new_y2 = min(image_height, y2 + margin * 0.2 * bbox_height) 
        return int(new_x1), int(new_y1), int(new_x2), int(new_y2)

class HeadSegmenter:
    def __init__(self, device='cpu'):
        self.device = device
        self.segmentation_pipeline = seg_pipeline.HumanHeadSegmentationPipeline(device=device)

    def segment_and_color(self, images, bg_color: List[int]=[0x79, 0x00, 0x30]) -> List[Image.Image]:
        """
        Args:
            List[numpy.ndarray]: A list of (cropped) images.  

        Returns:
            List[PIL.Image.Image]
        """
        segmented_images = []
        for image in images:
            segmented_image = self.segment_head(image, bg_color)
            segmented_images.append(Image.fromarray(segmented_image))
        return segmented_images

    def segment_head(self, image, bg_color: List[int] = [0x79, 0x00, 0x30]):
        segmentation_map = self.segmentation_pipeline.predict(image)
        segmentation_overlay = cv2.cvtColor(segmentation_map, cv2.COLOR_GRAY2RGB)
        segmentation_overlay[segmentation_map == 0] = bg_color
        result_image = np.where(segmentation_overlay == bg_color, segmentation_overlay, image)
        return result_image.astype('uint8')

def align_pil_image(img: Image.Image)->Image.Image:
    if hasattr(img, '_getexif'):
        exif = img._getexif()
        if exif is not None:
            orientation = exif.get(0x0112)
            if orientation == 3:
                img = img.transpose(Image.ROTATE_180)
            elif orientation == 6:
                img = img.transpose(Image.ROTATE_270)
            elif orientation == 8:
                img = img.transpose(Image.ROTATE_90)
    return img

def preprocess_image(images: List[Image.Image], bg: Background, face_detector: FaceDetector, head_segmenter: HeadSegmenter) -> List[Image.Image]:
    """

    Args:
        images (List[Image.Image]): A list of PIL.Image.Image.
        face_detector (FaceDetector): 
        head_segmenter (HeadSegmenter): 

    Returns:
        preprcessed_images (List[Image.Image]): A list of PIL.Image.Image.
    """
    if bg == Background.CRIMSON:
        bg_color = [0x79, 0x00, 0x30]
    elif bg == Background.IVORY:
        bg_color = [0xFF, 0xFF, 0xF0]
    elif bg == Background.BLACK:
        bg_color = [0x33, 0x33, 0x33]
    else:
        print("Invalid Background color", bg)
        raise ValueError("Invalid Background color")

    ndarr_images = [np.array(image) for image in images]
    
    results = face_detector.detect(ndarr_images)
    cropped_images = face_detector.crop_faces(results=results, image=ndarr_images, margin=2.5)
    processed_images = head_segmenter.segment_and_color(images=cropped_images, bg_color=bg_color)
    if os.environ.get('ENV') == 'dev':
        for idx, img in enumerate(processed_images):
            img.save(f'./preproc_{idx}_{bg.value}.jpg')
    return processed_images

face_detector: FaceDetector = None
head_segmenter: HeadSegmenter = None

if __name__ == "__main__":
    import time
    import cv2
    face_detector = FaceDetector('yolov8n-face.onnx')
    head_segmenter = HeadSegmenter('cuda')
    # a = [Image.open('test.jpg'), Image.open('source.png')]
    image_paths= ["./1.jpeg", "./2.jpeg", "./3.jpeg"]
    image_list = [
    cv2.cvtColor(cv2.imread(img_path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB) 
    for img_path in image_paths
    ]
    a = [Image.open('qwe.jpeg'),
        Image.open('qwe1.jpeg'),
        ]
    results = preprocess_image(a, face_detector, head_segmenter)
    # results = face_detector.detect(a)
    # cropped_images = face_detector.crop_faces(results=results, image=a, margin=2)
    # # cropped_images = [ x.resize((512, 512)) for x in cropped_images]
    # predicted_segmap = head_segmenter.segment_and_color(cropped_images)
    
    for i, result in enumerate(results):
        result.save(f'./test_{i}.jpg')
