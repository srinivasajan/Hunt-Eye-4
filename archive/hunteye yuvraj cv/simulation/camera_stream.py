import airsim
import cv2
import numpy as np

client = airsim.MultirotorClient()
client.confirmConnection()

while True:
    response = client.simGetImage("0", airsim.ImageType.Scene)

    img1d = np.frombuffer(response, dtype=np.uint8)

    img = cv2.imdecode(img1d, cv2.IMREAD_COLOR)

    cv2.imshow("Drone Camera", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()