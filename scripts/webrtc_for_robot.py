#!./ROSvenv/bin/env python3

import logging

"""my_own_handler = logging.StreamHandler()
my_own_handler.setLevel(logging.DEBUG)
my_own_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
my_own_handler.setFormatter(my_own_formatter)
aiortc_logger = logging.getLogger("aiortc")
aiortc_logger.addHandler(my_own_handler)
aiortc_logger.setLevel(logging.DEBUG)"""

import rospy
import time
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import warnings
import av.logging


# monkey patch av.logging.restore_default_callback
restore_default_callback = lambda *args: args
av.logging.restore_default_callback = restore_default_callback
av.logging.set_level(av.logging.DEBUG)
import asyncio
from asyncio import sleep
import aiortc
from aiortc import (
    RTCPeerConnection,
    RTCIceServer,
    RTCSessionDescription,
    RTCConfiguration,
    RTCDataChannel,
    RTCIceCandidate,
)
from aiortc.contrib.media import MediaPlayer
import firebase_admin
from firebase_admin import firestore_async, firestore, credentials
import threading


robotName = None
chosenPassword = None
dbpassword = None
offersdp = None
webcam = None
videosender = None
pub = None
rate = None
move_cmd = None
videoSize = "160x120"
videoCodec = "video/VP8"


ice_servers = [
    RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
    RTCIceServer(urls=["stun:a.relay.metered.ca:80"]),
    RTCIceServer(
        urls=["turn:a.relay.metered.ca:80"],
        username="dc6a654926f87d93d1d49211",
        credential="Oz/UT8fQ+zoK+pgB",
    ),
    RTCIceServer(
        urls=["turn:a.relay.metered.ca:80?transport=tcp"],
        username="dc6a654926f87d93d1d49211",
        credential="Oz/UT8fQ+zoK+pgB",
    ),
    RTCIceServer(
        urls=["turn:a.relay.metered.ca:443"],
        username="dc6a654926f87d93d1d49211",
        credential="Oz/UT8fQ+zoK+pgB",
    ),
    RTCIceServer(
        urls=["turn:a.relay.metered.ca:443?transport=tcp"],
        username="dc6a654926f87d93d1d49211",
        credential="Oz/UT8fQ+zoK+pgB",
    ),
]
configuration = RTCConfiguration(iceServers=ice_servers)


def dbinit():
    cred = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": "webrtc-for-robot",
            "private_key_id": "38e83821de91d443caaef04b0ccd316bbb0dd1af",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDazho1C5CovT6t\nnRQ4iJPsVCJ7whSTCQif8H8uTPswCn7DxOEP8xdZly4eTP2Lj243IYWRqVH3n/x6\n855G2qFPrAAgDfXdCojU63jD4qT3g0VszbthHVuj9tS89rKsq/352NWFz3aXVNKL\nA7gR0x1v1HuCEZ++KVYcM6/5DyLLq5MomIPVSKXWd5R3QCe4mKzm0omQ4zTsPejK\nte8iMKBxW32EC38mpimVMMylc2hS0kWzeq39ZmgddMLAzwM/dsM7CYLlJZTCHCOj\nzVGfglL7vr0FzgI23ZsK8rEnAzvaRgLCU1il3p0qj1icIwce3paW9AAvFpgZmMa5\n79YIV76nAgMBAAECggEAH0PI+eBrrLjR3nPuAj/9xwykmsN6NiJZ0aTHP4HveIdf\nYrDcqe9F3F7eT6UXq5v0lzsaf1xO4o/BP35VFPHDkANXRz1HbuzE7YuyB2d4xAdF\nYc0p47ASuqSX9GJZ2JOA6HUD2alx3CDaLtP6ts1QTPzzIvxKs5zreX8nO3LeuXRI\nno+PLa9PvqnuEvHBu6+heERK7dOw7v96X56vYv1PIpbdcgXib9/kJUbkE9Xry7yX\ncjcuzfqQ16AaBG0hDybIf1sNpCer+vFBguwWbC70lcYDMxHmOp/FKTgG20fQ0knJ\nIZs6W2yB00wxp6Wl31aG/PGeHPM3ABbubUstLm0flQKBgQDw4sWwEUalrEEQaMb+\nLvP+dDIKim+6l7uqON/ABYN3PXzGzf9tQmyOyTIpqBuI8AsXrftaA5s6qcYMnX5H\nBun0wRItuUDXUKxAaRmMjvgOEy+3+TChe4mfBTeRS6LlWbJLbGhtHyi5XpVb7TkA\npF3ifW3ZaCWMhUvYa58m6DOtuwKBgQDoiKiHpuhVNjyQhpkS3OqXn7ntnWr/BSar\nA5Xi9ZCojl67t4crt9j+gUfnkprYaRiV0BApEMKxt9X6Qv7KyLQujK1YLEEG6LCD\no743hLaW2H7POEwKkGGXM+mDhTDZqeh2xJU0eLsvuz7dWGykbwmZh1XDTv2DK+26\ndGEnzZ1uBQKBgCI7B36ipdhrJv/O8+AxCekx196Zl5D7eOaSmHEwF2N9cFrL8S00\nkDqmKqOyyN7nxZvC1IIRGyD1+TfXtZcgS2TFfvDSb31pcGDizoej1WoindhV5+w6\nou7fDetuxSI0YdrH9/rxv5a/8xeSGVSXBuRlkJOhchyK4KFLgd1Eh/t7AoGAIURr\n1/xpAMfhokufWrOAXHDdiMEcrZ9vCMhaiT3YlETKCNEY5YhH4yFbyCWRQaTHf6dk\nqHtdX0+NrWAoU5qjLIWzxwmNxA9GMY8bh5XVCX+vpLXJKzm8vIUQw2AqvPkx6Mv3\nDKq5HPsM413jLSM1nGFgQ7DpU/rU5/f+blNcUoECgYEA20F72w0upHlyyP6fqFzq\n6qnBG5lu4f51RvyysuljCVC2OislynYy+QlVi/Tii/zuKVUhSlP7KNDmxZuyJ2W0\n4SD7es7av3rEJS50Fb/DffW0lyKWmaSAoBjp9RCfVxIr/RT2MQIUcPEuUaoPHfrh\nW77fGK4WLVwHflmoon+vrl0=\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk-ofs4v@webrtc-for-robot.iam.gserviceaccount.com",
            "client_id": "101875506884262077763",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-ofs4v%40webrtc-for-robot.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com",
        }
    )
    app = firebase_admin.initialize_app(cred)
    db = firestore_async.client()
    db_ns = firestore.client()
    return db, db_ns


def openWebcam():
    global videosender, webcam
    try:
        if not webcam or webcam.video.readyState != "live":
            webcam = MediaPlayer("/dev/video0", options={"video_size": videoSize})   #1280x720 160x120 176x144 320x240 352x288 640x480
        print(webcam.__format__)
    except:
        print("Webcam unavailable!")

def force_codec(pc, sender, forced_codec):
    kind = forced_codec.split("/")[0]
    codecs = aiortc.RTCRtpSender.getCapabilities(kind).codecs
    transceiver = next(t for t in pc.getTransceivers() if t.sender == sender)
    transceiver.setCodecPreferences(
        [codec for codec in codecs if codec.mimeType == forced_codec]
    ) 

async def consumeOffer(peerconnection, offersdp, passwordattempt, db, doc_watch):
    print(passwordattempt, chosenPassword)
    if passwordattempt != chosenPassword:
        return
    offer = RTCSessionDescription(sdp=offersdp, type="offer")
    global videosender, webcam
    while not webcam or webcam.video.readyState != "live":
        time.sleep(1)
        openWebcam()
    videosender = peerconnection.addTrack(webcam.video)
    force_codec(peerconnection, videosender, videoCodec)

    print(await videosender.getStats())
    await peerconnection.setRemoteDescription(offer)

    @peerconnection.on("connectionstatechange")
    async def on_connectionstatechange():
        if peerconnection.connectionState == "closed":
            print("closed")

    answer = await peerconnection.createAnswer()
    await peerconnection.setLocalDescription(answer)
    print("answer:\n", answer.sdp)

    await db.collection(robotName).document("answer").set(
        {
            "type": peerconnection.localDescription.type,
            "sdp": peerconnection.localDescription.sdp,
        }
    )
    print("Answer in db.")
    doc_watch.unsubscribe()
    return


async def main(db, db_ns):
    i = 0
    f = 0
    k = 0
    previousConnectionState = "new"
    samePacketCount = 0
    prevpacketsSent = 0
    prevpacketsReceived = 0
    packetsSent = 0
    packetsReceived = 0
    datachannel = None

    peerconnection = RTCPeerConnection(configuration)

    callback_done = threading.Event()

    def on_snapshot(doc_snapshot, changes, read_time):
        # if peerconnection.connectionState != "connected":
        for doc in doc_snapshot:
            print(f"Received offer: {doc.id}")
            if doc.exists:
                global offersdp, dbpassword, videoSize, videoCodec
                offersdp = doc_ref.get().get("sdp")
                videoCodec = doc_ref.get().get("codec")
                videoSize = doc_ref.get().get("resolution")
                print(offersdp)
                dbpassword = doc_ref.get().get("password")
                print("Got", doc.get("type"), "!")
                doc_ref.delete()
                callback_done.set()

    doc_ref = db_ns.collection(robotName).document("offer")
    doc_watch = doc_ref.on_snapshot(on_snapshot)

    @peerconnection.on("datachannel")
    def on_datachannel(channel):
        print("added datachannel")
        print(channel.label)
        nonlocal datachannel
        if channel.label == "RTT":
            datachannelRTT = channel

            @datachannelRTT.on("message")
            def on_message(message):
                datachannelRTT.send(message)

        elif channel.label == "Robot control":
            datachannel = channel

            @datachannel.on("message")
            def on_message(message):
                print(message)
                rospy.loginfo(message)
                if isinstance(message, str) and message.startswith("control"):
                    if message == "control-up":
                        if move_cmd.linear.x < 0.22:
                            move_cmd.linear.x = move_cmd.linear.x + 0.01
                        else:
                            move_cmd.linear.x = 0.22
                        print(move_cmd.linear.x)
                    elif message == "control-down":
                        if move_cmd.linear.x > -0.22:
                            move_cmd.linear.x = move_cmd.linear.x - 0.01
                        else:
                            move_cmd.linear.x = -0.22
                        print(move_cmd.linear.x)
                    elif message == "control-left":
                        if move_cmd.angular.z < 2.79:
                            move_cmd.angular.z = move_cmd.angular.z + 0.05
                        else:
                            move_cmd.angular.z = 2.84
                        print(move_cmd.angular.z)
                    elif message == "control-right":
                        if move_cmd.angular.z > -2.79:
                            move_cmd.angular.z = move_cmd.angular.z - 0.05
                        else:
                            move_cmd.angular.z = -2.84
                        print(move_cmd.angular.z)
                    elif message == "control-stop":
                        move_cmd.linear.x = 0
                        move_cmd.angular.z = 0
                elif isinstance(message, str) and message.startswith("joyZ"):
                    move_cmd.linear.x = -0.22 * float(message[4:9])
                    move_cmd.angular.z = -2.00 * float(message[13:])

                if message == "endcall123455":
                    nonlocal f
                    f = 1

    while not rospy.is_shutdown():
        i = i + 1
        print(callback_done.is_set())
        if callback_done.is_set() == True and k == 0:
            await consumeOffer(peerconnection, offersdp, dbpassword, db, doc_watch)
            k = 1
        global videosender, webcam
        if peerconnection.connectionState != previousConnectionState:
            i = 0
        previousConnectionState = peerconnection.connectionState
        print("pc.connectionState:  ", peerconnection.connectionState, i)
        print("pc.iceConnectionState: ", peerconnection.iceConnectionState, i)
        if webcam:
            print("Webcam state :", webcam.video.readyState)
            print("\nResolution: ", videoSize,", codec: ", videoCodec,"\n")
        if (
            webcam
            and datachannel
            and webcam.video.readyState != "live"
            and datachannel.readyState == "open"
        ):
            datachannel.send("Reconnect46855")
            await peerconnection.close()
            break
        if i % 2 == 0 and peerconnection.connectionState == "connected":
            stats = await videosender.getStats()

            prevpacketsSent = packetsSent
            outbound_key = next(key for key in stats if "outbound" in key)
            packetsSent = stats[outbound_key].packetsSent
            print("packetsSent: ", packetsSent)

            prevpacketsReceived = packetsReceived
            transport_key = next(key for key in stats if "transport" in key)
            packetsReceived = stats[transport_key].packetsReceived
            print("packetsRecieved: ", packetsReceived, "\n")

            if packetsSent == prevpacketsSent or packetsReceived == prevpacketsReceived:
                samePacketCount = samePacketCount + 1
                print("same packet count:", samePacketCount)

            if samePacketCount >= 3:
                if datachannel and datachannel.readyState == "open":
                    datachannel.send("Reconnect46855")
                await peerconnection.close()
                break
        if (
            peerconnection
            and peerconnection.connectionState == "failed"
            or peerconnection.connectionState == "connecting"
            and i == 7
            or f == 1
        ):
            webcam.video.stop()
            await peerconnection.close()
            break
        j = 0
        while j < 20:
            pub.publish(move_cmd)
            # print("test1")
            await asyncio.sleep(0.1)
            # print("test2")
            j = j + 1
        print(" ")
    return


if __name__ == "__main__":
    db, db_ns = dbinit()
    loop = asyncio.get_event_loop()

    rospy.init_node("webrtc_for_robot", anonymous=False)

    pub = rospy.Publisher("cmd_vel", Twist, queue_size=10)
    rate = rospy.Rate(10)  # 10hz
    move_cmd = Twist()

    while True:
        robotName = input("Choose robot name:")
        chosenPassword = input("Choose a password:")
        if not (len(robotName) > 0 and len(chosenPassword) > 0):
            print("Password and robot name need to be at least one character long!\n")
        else:
            break
    try:
        while not rospy.is_shutdown():
            print("\n\n New loop \n\n")
            try:
                loop.run_until_complete(main(db, db_ns))
                if webcam:
                    webcam.video.stop()
                    webcam = None
            except KeyboardInterrupt:
                print("Received exit, exiting/n")
            """finally:
                print("One loop done!")
                print("rospy.is_shutdown():", rospy.is_shutdown())
                if rospy.is_shutdown():
                    print("Received exit, exiting/n")
                    loop.stop()
                    loop.close()
"""
    except KeyboardInterrupt:
        print("Received exit, exiting/n")
        loop.stop()
        loop.close()
