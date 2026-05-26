import airsim

client = airsim.MultirotorClient()
client.confirmConnection()

client.enableApiControl(True)
client.armDisarm(True)

client.takeoffAsync().join()

print("Drone took off")
