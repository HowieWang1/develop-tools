# import the necessary packages
from imutils.video import VideoStream
import numpy as np
import imutils
import time
import cv2
import os
from torchvision import datasets, transforms
import torchvision, torch
from PIL import Image
import torch.nn.functional as F

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def show_video():

    def face_detect(frame, faceNet):
        ####################################################
        #  下面进行人脸识别，只有识别出有人脸存在，才进行face mask检测
        ####################################################
        global face
        global j
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
        faceNet.setInput(blob)
        detections = faceNet.forward()
        faces = []
        locs = []
        preds = []
        # loop over the detections
        for i in range(0, detections.shape[2]):
            # the detection
            confidence = detections[0, 0, i, 2]  # 参数为置信度
            # 可以提高confidence，提高检测的效果
            if confidence > 0.5:
                # compute the (x, y)-coordinates of the bounding box for the object
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                # ensure the bounding boxes fall within the dimensions of the frame
                (startX, startY) = (max(0, startX), max(0, startY))
                (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

                # extract the face ROI, convert it from BGR to RGB channel
                # ordering, resize it to 224x224, and preprocess it
                face = frame[startY:endY, startX:endX]

                # face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
                # cent = np.array([list(startX,startY), list(endX,endY), list(startX,startY), list(startX,startY)])
                # cv2.drawContours(face, [cent], -1, (0, 255, 0), 2)
                cv2.imwrite("Outline{}.png".format(j), face)
                j += 1
                # face = cv2.resize(face, (224, 224))
                # face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
                # add the face and bounding boxes to their respective
                # lists
                faces.append(face)
                locs.append((startX, startY, endX, endY))
        if len(faces) > 0:
            # 先传入frame
            frame = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
            frame.save('testfile.png')
            img_t = transform(frame).unsqueeze(0)
            img_t = img_t.to(DEVICE)
            output = model(img_t)
            y = F.softmax(output, dim=1)
            _, predicted = torch.max(y, 1)
            preds = y.cpu().tolist()[0]
        return locs, preds

    ##############################
    # 加载模型
    prototxtPath = "deploy.prototxt"
    weightsPath = 'res10_300x300_ssd_iter_140000.caffemodel'
    ###############################
    model = torchvision.models.alexnet(pretrained=False)
    model.classifier[6] = torch.nn.Linear(model.classifier[6].in_features, 2)
    model.load_state_dict(torch.load('best_model.pth'))

    model = model.to(DEVICE)
    transform = transforms.Compose([
        transforms.ColorJitter(0.1, 0.1, 0.1, 0.1),
        transforms.Resize(255),  # resize 到255x255
        transforms.CenterCrop(244),  # Crop the image to 224×224 pixels about the center
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])  # 归一化处理 normalize
    vs = VideoStream(src=0).start()
    time.sleep(2.0)
    faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)
    global j
    j = 0
    while True:
        # grab the frame from the threaded video stream and resize it
        frame = vs.read()
        frame = imutils.resize(frame, width=400)

        # detect faces in the frame and determine if they are wearing a
        # face mask or not
        locs, preds = face_detect(frame, faceNet)
        # loop over the detected face locations and their corresponding locations
        for (box, pred) in zip(locs, preds):
            # unpack the bounding box and predictions
            (startX, startY, endX, endY) = box
            (mask, withoutMask) = preds
            label = "Mask" if mask > withoutMask else "No Mask"
            color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

            # include the probability in the label
            label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

            # display the label and bounding box rectangle on the output frame
            cv2.putText(frame, label, (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

        # show the output frame
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break


if __name__ == "__main__":
    show_video()
