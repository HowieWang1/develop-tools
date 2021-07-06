import torch
import torchvision
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
import torchvision.models as models

print(torch.__version__)


def get_the_model():  # define some parameters
    BATCH_SIZE = 10  # 一次加载数据的量
    NUM_EPOCHS = 20  # 一共循环多少次

    BEST_MODEL_PATH = 'best_model.pth'
    best_accuracy = 0.0
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # 判断是用cpu还是用gpu

    dataset = datasets.ImageFolder(
        './COVID-19',
        transforms.Compose([
            transforms.ColorJitter(0.1, 0.1, 0.1, 0.1),
            transforms.Resize(255),  # resize 到255x255
            transforms.CenterCrop(244),  # Crop the image to 224×224 pixels about the center
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])  # 归一化处理
        ])
    )
    train_dataset, test_dataset = torch.utils.data.random_split(dataset, [len(dataset) - 50, 50])

    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
    )

    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
    )

    model = models.alexnet(pretrained=True)  # 卷积神经网络模型
    model.classifier[6] = torch.nn.Linear(model.classifier[6].in_features, 2)  # 做线性变换输入为4096，输出为2
    model = model.to(DEVICE)  # 转移到DEVICE上去

    optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)
    # 优化器选择随机梯度下降

    for epoch in range(NUM_EPOCHS):
        for images, labels in iter(train_loader):
            images = images.to(DEVICE)
            labels = labels.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(images)
            loss = F.cross_entropy(outputs, labels)
            loss.backward()
            optimizer.step()

        test_error_count = 0.0
        for images, labels in iter(test_loader):
            images = images.to(DEVICE)
            labels = labels.to(DEVICE)
            outputs = model(images)
            test_error_count += float(torch.sum(torch.abs(labels - outputs.argmax(1))))

        test_accuracy = 1.0 - float(test_error_count) / float(len(test_dataset))
        print('%d: %f' % (epoch, test_accuracy))
        if test_accuracy > best_accuracy:
            torch.save(model.state_dict(), BEST_MODEL_PATH)
            best_accuracy = test_accuracy


if __name__ == "__main__":
    get_the_model()