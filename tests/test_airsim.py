import pytest
import sys
import os

sys.path.insert(0, os.path.abspath('src'))

airsim = pytest.importorskip("airsim")


def test_airsim_takeoff_connection():
    client = airsim.MultirotorClient()
    try:
        client.confirmConnection()
    except Exception as error:
        pytest.skip(f"AirSim simulator is not reachable: {error}")

    client.enableApiControl(True)
    client.armDisarm(True)

    client.takeoffAsync().join()

    print("Drone took off")
