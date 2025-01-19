# Runs on the ground station
import cv2, imutils, socket
import numpy as np
import time
import base64

BUFF_SIZE = 65536
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
print(host_ip)
port = 9999
message = b"Hello"

testmode = (
    1  # To display images to verify. Set to zero if not intrested in displaying images.
)
StepSize = 3

frame_width = 800
frame_height = 600

# make_chunks function creats chunks.
# inputs -- EdgeArray and the size_of_chunk to create.
# output -- yield successive n-sized chunks.
def make_chunks(EdgeArray, size_of_chunk):
    chunks = []
    for i in range(0, len(EdgeArray), size_of_chunk):
        chunks.append(EdgeArray[i : i + size_of_chunk])
    return chunks


client_socket.sendto(message, (host_ip, port))
fps, st, frames_to_count, cnt = (0, 0, 20, 0)
while True:
    packet, _ = client_socket.recvfrom(BUFF_SIZE)
    data = base64.b64decode(packet, " /")
    npdata = np.fromstring(data, dtype=np.uint8)
    frame = cv2.imdecode(npdata, 1)
    frame = cv2.putText(
        frame,
        "FPS: " + str(fps),
        (10, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2,
    )
    # cv2.imshow("RECEIVING VIDEO", frame)
    frame = cv2.resize(frame, (frame_width, frame_height))
    original_frame = (
        frame.copy()
    )  # Copy of frame which will be used for to compare with other images after appling various operations.
    img_edgerep = (
        frame.copy()
    )  # Copy of frame which will be used for edge representation.
    img_contour = frame.copy()  # Copy of frame which will be used for drawing contours.
    img_navigation = (
        frame.copy()
    )  # Copy of frame which will be used for indicating direction of navigation.

    blur = cv2.bilateralFilter(
        img_edgerep, 9, 40, 40
    )  # Blurring the image to remove the noise present in the image.
    edges = cv2.Canny(blur, 50, 100)  # Obtaining clear edges using canny edge detector.

    img_edgerep_h = (
        img_edgerep.shape[0] - 1
    )  # Storing the height of the image which will be used in for loop.
    img_edgerep_w = (
        img_edgerep.shape[1] - 1
    )  # Storing the width of the image which will be used in for loop.

    EdgeArray = (
        []
    )  # Initilizing the array to store the concerned edges for edge representation.

    for j in range(
        0, img_edgerep_w, StepSize
    ):  # FOR loop along the width of the image with given stepsize.
        pixel = (
            j,
            0,
        )  # If no edge found in column this value will be stored in edgearray.
        for i in range(
            img_edgerep_h - 5, 0, -1
        ):  # FOR loop along the height of the image.
            if edges.item(i, j) == 255:  # Checking for edges.
                pixel = (j, i)
                break  # If edge is found break and go for the next colomn.
        EdgeArray.append(pixel)  # Store the eged detected in EgdeArray.

    for x in range(
        len(EdgeArray) - 1
    ):  # Joining each edge to diferentiate the frame into free space and conjusted space(with objects)
        cv2.line(img_edgerep, EdgeArray[x], EdgeArray[x + 1], (0, 255, 0), 1)

    for x in range(
        len(EdgeArray)
    ):  # Joining each point in the EdgeArray to the respective bottom edge of the frame to represent free space for the bot to move around
        cv2.line(
            img_edgerep, (x * StepSize, img_edgerep_h), EdgeArray[x], (0, 255, 0), 1
        )

    # Code to draw contours.

    blurred_frame = cv2.bilateralFilter(img_contour, 9, 75, 75)
    gray = cv2.cvtColor(blurred_frame, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(gray, 106, 255, 1)
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(img_edgerep, contours, -1, (0, 0, 255), 3)

    # Code to decide direction of navigation

    number_of_chunks = 3
    size_of_chunk = int(len(EdgeArray) / number_of_chunks)
    chunks = make_chunks(
        EdgeArray, size_of_chunk
    )  # Calling make_chunks function to create the chunks.
    avg_of_chunk = []
    for i in range(len(chunks) - 1):
        x_vals = []
        y_vals = []
        for (x, y) in chunks[i]:  # Storing the x and y value saperatly to find average.
            x_vals.append(x)
            y_vals.append(y)
        avg_x = int(np.average(x_vals))
        avg_y = int(np.average(y_vals))
        avg_of_chunk.append([avg_y, avg_x])
        cv2.line(
            frame,
            (int(img_edgerep_w / 2), img_edgerep_h),
            (avg_x, avg_y),
            (255, 0, 0),
            2,
        )  # Draw lines to each average chunks to decide the direction of navigation.

    forwardEdge = avg_of_chunk[1]
    cv2.line(
        frame,
        (int(img_edgerep_w / 2), img_edgerep_h),
        (forwardEdge[1], forwardEdge[0]),
        (0, 255, 0),
        3,
    )
    farthest_point = min(avg_of_chunk)
    # print(farthest_point)

    if forwardEdge[0] > 250:  # Checking for the object at the front is close to bot.
        if (
            farthest_point[1] < 310
        ):  # Checking for the farthest_point on the left of the frame.
            direction = "Move left "
            # print(direction)
        else:
            direction = "Move right "
            # print(direction)
    else:
        direction = "Move forward "
        print(direction)
    message = str.encode(direction)
    client_socket.sendto(message, (host_ip, port))
        # Code to display the results

    if testmode == 1:
        cv2.imshow("Original_Frame", original_frame)
        cv2.imshow("Canny", edges)
        cv2.imshow("Threshold", thresh)
        cv2.imshow("Edge_separation", img_edgerep)
        font = cv2.FONT_HERSHEY_SIMPLEX
        navigation = cv2.putText(
            frame, direction, (275, 50), font, 1, (0, 0, 255), 2, cv2.LINE_AA
        )
        cv2.imshow("Navigation", navigation)

    k = cv2.waitKey(5) & 0xFF
    if k == 27 or k == ord("q"):
        break
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        client_socket.close()
        break
    if cnt == frames_to_count:
        try:
            fps = round(frames_to_count / (time.time() - st))
            st = time.time()
            cnt = 0
        except:
            pass
    cnt += 1

cv2.destroyAllWindows
# cap.release()

