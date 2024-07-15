import cv2
import depthai
import torch


def create_pipeline(res):
    pipeline = depthai.Pipeline()

    cam_rgb = pipeline.createColorCamera()
    cam_rgb.setPreviewSize(res, res)
    cam_rgb.setInterleaved(False)

    st_left = pipeline.createMonoCamera()
    st_left.setCamera("left")
    st_left.setResolution(depthai.MonoCameraProperties.SensorResolution.THE_400_P)

    st_right = pipeline.createMonoCamera()
    st_right.setCamera("right")
    st_right.setResolution(depthai.MonoCameraProperties.SensorResolution.THE_400_P)

    depth = pipeline.createStereoDepth()
    depth.setLeftRightCheck(True)
    depth.setExtendedDisparity(False)
    depth.setSubpixel(False)
    st_left.out.link(depth.left)
    st_right.out.link(depth.right)

    """
    imu = pipeline.createIMU()
    imu.enableIMUSensor([depthai.IMUSensor.ROTATION_VECTOR], 10)
    imu.setBatchReportThreshold(1)
    imu.setMaxBatchReports(1)
    """

    xout_rgb = pipeline.createXLinkOut()
    xout_rgb.setStreamName("rgb")
    cam_rgb.preview.link(xout_rgb.input)

    xout_depth_fac = pipeline.createXLinkOut()
    xout_depth_fac.setStreamName("depth_fac")
    depth.disparity.link(xout_depth_fac.input)

    xout_depth_dist = pipeline.createXLinkOut()
    xout_depth_dist.setStreamName("depth_dist")
    depth.depth.link(xout_depth_dist.input)

    xout_depth_conf = pipeline.createXLinkOut()
    xout_depth_conf.setStreamName("depth_conf")
    depth.confidenceMap.link(xout_depth_conf.input)

    """
    xout_imu = pipeline.createXLinkOut()
    xout_imu.setStreamName("imu")
    imu.out.link(xout_imu.input)
    """

    return pipeline


class PipelineWrapper:
    """
    Handles creating and reading all queues.
    """

    def __init__(self, device):
        self.device = device
        self.names = ["rgb", "depth_fac", "depth_dist", "depth_conf"]
        self.queues = {}
        for name in self.names:
            queue = self.device.getOutputQueue(name)
            queue.setMaxSize(1)
            queue.setBlocking(False)
            self.queues[name] = queue

    def get(self):
        ret = {}
        for name in self.names:
            frame = self.queues[name].get()
            if name == "rgb":
                frame = frame.getCvFrame()
            else:
                frame = crop_resize(frame.getFrame())
            ret[name] = frame

        return ret


def crop_resize(img):
    """
    img: HWC
    """
    diff = img.shape[1] - img.shape[0]
    img = img[:, diff // 2 : -diff // 2]
    img = cv2.resize(img, (256, 256))
    return img


def images_to_tensor(images):
    """
    Process return of PipelineWrapper.get() into tensor input for model.

    Return:
        (4, 256, 256), CHW
        uint8, 0 to 255
    """
    x = torch.empty((4, 256, 256), dtype=torch.uint8)
    x[0:3] = torch.tensor(images["rgb"]).permute(2, 0, 1)
    x[3] = torch.tensor(images["depth_fac"])
    return x
