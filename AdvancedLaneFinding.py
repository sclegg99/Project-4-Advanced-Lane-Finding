#!/usr/bin/env python3# -*- coding: utf-8 -*-"""Created on Fri Jul  7 09:52:15 2017@author: sclegg1. Input camera and distortion matrix.2. Read image then undistort and warp3. Split image into seperate color channels4. Apply gradient operator to color channel(s)5. Plot data"""import numpy as npimport scipyimport cv2import matplotlib.pyplot as pltimport sys, getoptimport pickle# Define a class to receive the characteristics of each line detectionclass Lane():    def __init__(self):        # was the line detected in the last iteration?        self.detected = False          # number of frames without detection        self.notdetected = 0        # x values of the last n fits of the line        self.recent_xfitted = np.empty(0)         #average x values of the fitted line over the last n iterations        self.bestx = None         #std polynomial coefficients averaged over the last n iterations        self.std_fit = None        #polynomial coefficients averaged over the last n iterations        self.average_fit = None          #polynomial coefficients for the most recent fit        self.current_fit = [np.array([False])]          #radius of curvature of the line in some units        self.radius_of_curvature = None         #distance in meters of vehicle center from the line        self.line_base_pos = None        #direction of turn (left vs right)        self.direction = None         #difference in fit coefficients between last and new fits        self.diffs = np.array([0,0,0], dtype='float')         #x values for detected line pixels        self.allx = None          #y values for detected line pixels        self.ally = None# define x and y scaling for pixelsscaleX = 3.1/114.scaleY = 14.1/90.scaleR = 1.0# Routine for getting the perspective transformation given# the source (src) and destination (dst) points.# The routine returns the transform matrix (M) and# inverse transform matrix (Minv).def get_transform(src, dst):    M = cv2.getPerspectiveTransform(src, dst)    Minv = cv2.getPerspectiveTransform(dst, src)    return M, Minv# Define a function that applies Sobel x or y, # then takes an absolute value and applies a threshold.# Note: calling your function with orient='x', thresh_min=5, thresh_max=100# should produce output like the example image shown above this quiz.def abs_sobel_thresh(gray, orient='x', sobel_kernel=3, thresh=(0, 255)):        # Apply the following steps to img        # 2) Take the derivative in x or y given orient = 'x' or 'y'    if orient == 'x':        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=sobel_kernel)    else:        sobel = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=sobel_kernel)    # 3) Take the absolute value of the derivative or gradient    abs_sobel = np.absolute(sobel)        # 4) Scale to 8-bit (0 - 255) then convert to type = np.uint8    scaled_sobel = np.uint8(255*abs_sobel/np.max(abs_sobel))        # 5) Create a mask of 1's where the scaled gradient magnitude     # is > thresh[0] and < thresh[1]    sbinary = np.zeros_like(scaled_sobel)    sbinary[(scaled_sobel >= thresh[0]) & (scaled_sobel <= thresh[1])] = 1    # 6) Return this mask as your binary_output image    return sbinary# Define a function that applies Sobel x and y, # then computes the magnitude of the gradient# and applies a thresholddef mag_thresh(gray, sobel_kernel=3, mag_thresh=(100, 200)):        # Apply the following steps to img     # 2) Take the gradient in x and y separately    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=sobel_kernel)    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=sobel_kernel)        # 3) Calculate the magnitude    mag_sobel = np.sqrt(sobelx*sobelx + sobely*sobely)        # 4) Scale to 8-bit (0 - 255) and convert to type = np.uint8    scaled_sobel = np.uint8(255*mag_sobel/np.max(mag_sobel))        # 5) Create a binary mask where mag thresholds are met    mbinary = np.zeros_like(scaled_sobel)    mbinary[(scaled_sobel >= mag_thresh[0]) & (scaled_sobel <= mag_thresh[1])] = 1        # 6) Return this mask as your binary_output image    return mbinary# Define a function that applies Sobel x and y, # then computes the direction of the gradient# and applies a threshold.def dir_threshold(gray, sobel_kernel=3, thresh=(np.pi/4, np.pi/2)):        # Apply the following steps to img     # 2) Take the gradient in x and y separately    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=sobel_kernel)    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=sobel_kernel)        # 3) Take the absolute value of the x and y gradients    abs_sobelx = np.absolute(sobelx)    abs_sobely = np.absolute(sobely)        # 4a) Use np.arctan2(abs_sobely, abs_sobelx) to calculate the direction of the gradient     dir_sobel = np.arctan2(abs_sobely, abs_sobelx)        # 4b) Scale to 8-bit (0 - 255) then convert to type = np.uint8    scaled_dir = np.uint8(255*dir_sobel/np.max(dir_sobel))        # 5) Create a binary mask where mag thresholds are met    dbinary = np.zeros_like(scaled_dir)    dbinary[(scaled_dir >= thresh[0]) & (scaled_dir <= thresh[1])] = 1        # 6) Return this mask as your binary_output image    return dbinary# undistort the img image give the camera# matrix and distortion coefficientsdef un_distort(img, mtx, dist):    h,  w = img.shape[:2]    newcameramtx, roi=cv2.getOptimalNewCameraMatrix(mtx,dist,(w,h),1,(w,h))    # undistort    dst = cv2.undistort(img, mtx, dist, None, newcameramtx)    return dst# distort the img image given the camera# matrix and distortion coefficientsdef distort(img, mtx, dist):    h,  w = img.shape[:2]    newcameramtx, roi=cv2.getOptimalNewCameraMatrix(mtx,dist,(w,h),1,(w,h))    # undistort    shape = (img.shape[1],img.shape[0])    mapx ,mapy = cv2.initUndistortRectifyMap(newcameramtx, dist, None, mtx, shape, cv2.CV_32FC1)    dst = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR)    return dst# Edit this function to create your own pipeline.def pipeline(img, leftLane, rightLane, clahe, vertices, M, Minv, img_size,             c_thresh=(150, 250), sx_thresh=(150, 250)):    #   convert image to YCrCb color space then extract the Y channel    gray = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb )[:,:,0]#    gray = cv2.cvtColor(img, cv2.COLOR_BGR2HLS )[:,:,2]        # Apply contrast limited adaptive histogram equalization to image#    gray = clahe.apply(gray)            ksize = 9 # Kernel size for x and y sobel gradients        # Sobel X (use clahe output)    sxbinary = abs_sobel_thresh(gray, orient='x', sobel_kernel=ksize,                                thresh=sx_thresh)        # Sobel Y (don't use clahe)    sybinary = abs_sobel_thresh(gray, orient='y', sobel_kernel=ksize,                                thresh=sx_thresh)       # Sobel Magnitude (use clahe)#    mag_binary = mag_thresh(gray, sobel_kernel=9, mag_thresh=c_thresh)#    dir_binary = dir_threshold(gray, sobel_kernel=9)    # Stack each channel    # Note color_binary[:, :, 0] is all 0s, effectively an all black image. It might    # be beneficial to replace this channel with something else.    combined_binary = 2*sxbinary + sybinary    combined_binary = np.uint8(255*combined_binary/np.max(combined_binary))#    ax2.imshow(combined_binary)#    cv2.waitkey()    # Open then close contours#    kernel = np.ones((3,3),np.uint8)#    opened = cv2.dilate(cv2.erode(combined_binary,kernel),kernel)    kernel = np.ones((3,3),np.uint8)    closed = cv2.erode(cv2.dilate(combined_binary,kernel),kernel)#    closed = combined_binary    # Warp image to get birds-eye view    warped = cv2.warpPerspective(closed, M, img_size, flags=cv2.INTER_LINEAR)#    warped = closed    # create mask for perspective image.  If lanes are detected, then    # make the mask adept to the preditected lane curvature    if leftLane.detected and rightLane.detected:        mask = mask_lane(img, leftLane.average_fit, rightLane.average_fit)    else:    # default mask of just lane markings        mask = np.uint8(np.zeros((img_size[1],img_size[0])))        ignore_mask_color = 255        cv2.fillPoly(mask, vertices, ignore_mask_color)            # mask image and trim it to remove the masked out portion    masked = cv2.bitwise_and(warped, mask)    masked = masked[360:759,320:960]    # get lane boundaries    leftLane, rightLane = find_the_lane(masked, leftLane, rightLane)        # create lane boundary plot and warp perspective from birds-eye to    # camera view    left_average = leftLane.average_fit    right_average = rightLane.average_fit    lanes = plot_lane(img, left_average, right_average)    lanes = cv2.warpPerspective(lanes, Minv, img_size, flags=cv2.INTER_LINEAR)    return lanes, leftLane, rightLane# Guts of Udacity routine for locating the lanes and caculating their curvature.def find_the_lane(binary_warped, leftLane, rightLane):    # Choose the number of sliding windows    nwindows = 9        # Set height of windows    window_height = np.int(binary_warped.shape[0]/nwindows)    # Set the width of the windows +/- margin    margin = 25        # Set minimum number of pixels found to recenter window    minpix = 50        # Get data stored in Lanes    left_fit = leftLane.average_fit    right_fit = rightLane.average_fit        # if left or right lane is not detected    if not leftLane.detected or not rightLane.detected:        # Assuming you have created a warped binary image called "binary_warped"        # Take a histogram of the bottom half of the image        midpt = int(binary_warped.shape[0]/2)        histogram = np.sum(binary_warped[midpt:,:], axis=0)                # Find the peak of the left and right halves of the histogram        # These will be the starting point for the left and right lines        midpoint = np.int(histogram.shape[0]/2)        leftx_base = np.argmax(histogram[:midpoint])        rightx_base = np.argmax(histogram[midpoint:]) + midpoint            # Identify the x and y positions of all nonzero pixels in the image        nonzero = binary_warped.nonzero()        nonzeroy = np.array(nonzero[0])        nonzerox = np.array(nonzero[1])                # Current positions to be updated for each window        leftx_current = leftx_base        rightx_current = rightx_base               # Create empty lists to receive left and right lane pixel indices        left_lane_inds = []        right_lane_inds = []                # Step through the windows one by one        for window in range(nwindows):            # Identify window boundaries in x and y (and right and left)            win_y_low = binary_warped.shape[0] - (window+1)*window_height            win_y_high = binary_warped.shape[0] - window*window_height            win_xleft_low = leftx_current - margin            win_xleft_high = leftx_current + margin            win_xright_low = rightx_current - margin            win_xright_high = rightx_current + margin                # Identify the nonzero pixels in x and y within the window            good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)).nonzero()[0]            good_right_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)).nonzero()[0]                # Append these indices to the lists            left_lane_inds.append(good_left_inds)            right_lane_inds.append(good_right_inds)                # If you found > minpix pixels, recenter next window on their mean position            if len(good_left_inds) > minpix:                leftx_current = np.int(np.mean(nonzerox[good_left_inds]))            if len(good_right_inds) > minpix:                        rightx_current = np.int(np.mean(nonzerox[good_right_inds]))                # Concatenate the arrays of indices        left_lane_inds = np.concatenate(left_lane_inds)        right_lane_inds = np.concatenate(right_lane_inds)                # Extract left and right line pixel positions        leftx = nonzerox[left_lane_inds]        lefty = nonzeroy[left_lane_inds]        rightx = nonzerox[right_lane_inds]        righty = nonzeroy[right_lane_inds]        if lefty.size < 100 or righty.size < 100:            left_fit = np.array(leftLane.average_fit)            right_fit = np.array(rightLane.average_fit)            print('*** Skip frame *** Step A {} {}'.format(lefty.size,righty.size))            leftLane.detected = False            rightLane.detected = False            leftLane.nodetected += 1            rightLane.nodetected += 1        else:            # Fit a second order polynomial to each            left_fit, covar = scipy.optimize.curve_fit(f_curve, lefty, leftx)            right_fit, covar = scipy.optimize.curve_fit(f_curve, righty, rightx)                    # Set lane detected to True            leftLane.detected = True            rightLane.detected = True            leftLane.nodetected = 0            rightLane.nodetected = 0    else:        # Assume you now have a new warped binary image         # from the next frame of video (also called "binary_warped")        # It's now much easier to find line pixels!        nonzero = binary_warped.nonzero()        nonzeroy = np.array(nonzero[0])        nonzerox = np.array(nonzero[1])        left_lane_inds = ((nonzerox > (f_curve(nonzeroy, *left_fit) - margin)) & (nonzerox < (f_curve(nonzeroy, *left_fit) + margin)))         right_lane_inds = ((nonzerox > (f_curve(nonzeroy, *right_fit) - margin)) & (nonzerox < (f_curve(nonzeroy, *right_fit) + margin)))                  # Again, extract left and right line pixel positions        leftx = nonzerox[left_lane_inds]        lefty = nonzeroy[left_lane_inds]        rightx = nonzerox[right_lane_inds]        righty = nonzeroy[right_lane_inds]                if lefty.size < 100 or righty.size < 100:            left_fit = np.array(leftLane.average_fit)            right_fit = np.array(rightLane.average_fit)            print('*** Skip frame *** Step B {} {}'.format(lefty.size,righty.size))            leftLane.detected = False            rightLane.detected = False        else:            # Fit a second order polynomial to each            left_fit, covar = scipy.optimize.curve_fit(f_curve, lefty, leftx)            right_fit, covar = scipy.optimize.curve_fit(f_curve, righty, rightx)                        # Set lane detected to True            leftLane.detected = True            leftLane.nodetected = 0            rightLane.detected = True            rightLane.nodetected = 0    # Store lane data    leftLane.current_fit = left_fit    rightLane.current_fit = right_fit    leftLane.recent_xfitted = storeData(leftLane.recent_xfitted, left_fit, 9)    rightLane.recent_xfitted = storeData(rightLane.recent_xfitted, right_fit, 9)    left_average = np.mean(leftLane.recent_xfitted, axis=0).tolist()    right_average = np.mean(rightLane.recent_xfitted, axis=0).tolist()    leftLane.std_fit = np.std(leftLane.recent_xfitted, axis=0)    rightLane.std_fit = np.std(rightLane.recent_xfitted, axis=0)    leftLane.average_fit = left_average    rightLane.average_fit = right_average    leftLane.line_base_pos = (f_curve(359, *left_average)-319)*scaleX    rightLane.line_base_pos = (f_curve(359, *right_average)-319)*scaleX    laneWidth = np.abs(1.0-np.abs(rightLane.line_base_pos-leftLane.line_base_pos)/3.1)    if laneWidth > 0.05:        print('*** Resetting *** Lane width difference exceeds 5% {:7.2f}'.format(laneWidth*100.))        leftLane.detected = False        rightLane.detected = False            leftLane.direction = np.sign((f_curve(0, *left_average)-319)*scaleX-leftLane.line_base_pos)    rightLane.direction = np.sign((f_curve(0, *right_average)-319)*scaleX-rightLane.line_base_pos)    # calcualate and store radius of curvature    leftLane.radius_of_curvature = np.mean(curvature(lefty, *left_average))*scaleR    rightLane.radius_of_curvature = np.mean(curvature(righty, *right_average))*scaleR    return leftLane, rightLanedef storeData(x, i, N):    length = x.shape[0]    nCoeff = i.size    if length < N:        x = np.append(x, i)        x = np.reshape(x, (length+1, nCoeff))    else:        x = np.roll(x, -1, axis=0)        x[-1] = i    return xdef f_curve(x, a0, a1, a2):    return a0 + (x-719)*a1*x#    return a0 + a1*x + a2*x*xdef curvature(x, a0, a1, a2):    return np.abs(np.power((1.+np.power((2.*x-719)*a1,2)),1.5)/(2.*a1))#    return np.abs(np.power(1.+np.power(a1+2.*a2*x,2),1.5)/(2.*a2))def plot_lane(img, left_arc_params, right_arc_params):    # Generate x and y values for plotting. Note: fit parameters are based    # on reduced sized image hence the need to scale ploty, etc.    ploty = np.linspace(int(img.shape[0]*8/10), int(img.shape[0]-1), int(img.shape[0]*8/10) )    left_edge = f_curve(ploty-img.shape[0]/2, *left_arc_params)+img.shape[1]/4    right_edge = f_curve(ploty-img.shape[0]/2, *right_arc_params)+img.shape[1]/4       # Create an image to draw on and an image to show the selection window    lane_image = np.zeros_like(img)    # Generate a polygon to illustrate the area between the left and rigth lanes    # And recast the x and y points into usable format for cv2.fillPoly()    left_lane_curve = np.array([np.transpose(np.vstack([left_edge, ploty]))])    right_lane_curve = np.array([np.flipud(np.transpose(np.vstack([right_edge, ploty])))])    lane_pts = np.hstack((left_lane_curve, right_lane_curve))    cv2.fillPoly(lane_image, np.int_([lane_pts]), (0,255,0))    return lane_imagedef mask_lane(img, left_fit, right_fit):    # Generate x and y values for plotting. Note: fit parameters are based    # on reduced sized image hence the need to scale ploty, etc.    ploty = np.linspace(int(img.shape[0]*.5), int(img.shape[0]-10), int(img.shape[0]*.5-10) )    left_fitx_left  = f_curve(ploty-img.shape[0]/2, *left_fit)+img.shape[1]/4-5    left_fitx_right = f_curve(ploty-img.shape[0]/2, *left_fit)+img.shape[1]/4+5        right_fitx_left  = f_curve(ploty-img.shape[0]/2, *right_fit)+img.shape[1]/4-5    right_fitx_right = f_curve(ploty-img.shape[0]/2, *right_fit)+img.shape[1]/4+5    # Create an image to draw on and an image to show the selection window    mask = np.uint8(np.zeros((img.shape[0],img.shape[1])))    ignore_mask_color = 255    # Generate a polygon to illustrate the area between the left and rigth lanes    # And recast the x and y points into usable format for cv2.fillPoly()    left_lane_curve_left   = np.array([np.transpose(np.vstack([left_fitx_left, ploty]))])    left_lane_curve_right  = np.array([np.flipud(np.transpose(np.vstack([left_fitx_right, ploty])))])    right_lane_curve_left  = np.array([np.transpose(np.vstack([right_fitx_left, ploty]))])    right_lane_curve_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx_right, ploty])))])        left_lane_pts  = np.hstack(( left_lane_curve_left,  left_lane_curve_right))    right_lane_pts = np.hstack((right_lane_curve_left, right_lane_curve_right))    cv2.fillPoly(mask, np.int_([ left_lane_pts]), ignore_mask_color)    cv2.fillPoly(mask, np.int_([right_lane_pts]), ignore_mask_color)    return maskdef model(inputfile, outputfile, cameradata):    # Set constract limited adaptive histogram parameters    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))       vidin = cv2.VideoCapture(inputfile)    # Check if camera opened successfully    if (vidin.isOpened()== False):         print("Error opening video stream or file")        exit()    width = int(vidin.get(3))    height = int(vidin.get(4))    fps = int(vidin.get(5))    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')    vidout = cv2.VideoWriter(outputfile, fourcc, fps, (width, height))                # Code for reading video    # Create a couple of video windows. One to display input the other to display output    cv2.namedWindow('OutputVideo')    cv2.moveWindow('OutputVideo', 700, 300)    image_shape = (width, height) # define image size        # define default vertices of poly mask    vert0 = [ 560, 710]    vert1 = [ 560, 300]    vert2 = [ 590, 300]    vert3 = [ 590, 710]    vert4 = [ 680, 710]    vert5 = [ 680, 300]    vert6 = [ 710, 300]    vert7 = [ 710, 710]    vertices = np.array([[vert0, vert1, vert2, vert3,                          vert4, vert5, vert6, vert7]], dtype=np.int32)    # Define threshold values    sxy_thresh = (50, 200)    mag_thresh = (70, 150)        # read camera data    camera_pickle = pickle.load(open(cameradata, 'rb'))    mtx = camera_pickle["mtx"]    dist= camera_pickle["dist"]    print("Got Camera Data")        # Create transformation matrix for wrapping image to birds-eye    # view and inverse transform for unwrapping from birds-eye    # First set src and dst vectors based on image analysis of     # straight lane images    src = np.float32([[972.296, 613.839],                      [697.561, 442.204],                      [626.414, 442.204],                      [372.814, 613.839]])        offset_x = (image_shape[0]-137)/2    offset_y = image_shape[1]-300        dst = np.float32([[116+offset_x,286+offset_y],                      [114+offset_x,  0+offset_y],                      [  2+offset_x,  0+offset_y],                      [  0+offset_x,286+offset_y]])        # generate perspective transform and inverse transform matrices    M, Minv = get_transform(src, dst)        # font for writing on image    font = cv2.FONT_HERSHEY_SIMPLEX    textPosition = (10, 50)        # define left and right lane from Lane class and     leftLane = Lane()    rightLane = Lane()        success = True    while success:                # get image        success, image = vidin.read()        if image is None:            break                # Undistort image        undistorted_image = un_distort(image, mtx, dist)        # process image through pipeline        lanes, leftLane, rightLane = pipeline(undistorted_image, leftLane, rightLane, clahe,                         vertices, M, Minv, image_shape,                         c_thresh=mag_thresh,                         sx_thresh=sxy_thresh)                # redistort lane image then superimpose on the original camera image        lanes1 = distort(lanes, mtx, dist)            result = cv2.addWeighted(image, 1, lanes1, 0.3, 0)                # add text to image#        print('{:10.2f} {:10.2f}'.format(leftLane.radius_of_curvature,rightLane.radius_of_curvature))               radius = .5*(leftLane.radius_of_curvature+rightLane.radius_of_curvature)        center = .5*(leftLane.line_base_pos+rightLane.line_base_pos)        if np.isnan(radius):            radius = 10000.        if(leftLane.direction < 0):            direction = 'left'        else:            direction = 'right'        if radius > 3000.:            text = "Straight, Distance to lane center {:5.2f}m".format(center)        else:            text = "Radius of curvature: {:7.2f}m to the {}, Distance to lane center {:5.2f}m".format(radius,direction,center)        cv2.putText(result, text, textPosition, font, 1, (255,255,255), 2, cv2.LINE_AA)        # display undistored image and read next frame        # Display the resulting frame                udst_2 = cv2.resize(result, (0,0), fx=0.5, fy=0.5)                    cv2.imshow('OutputVideo',udst_2)        cv2.waitKey(1)        vidout.write(result)            # When everything done, release the video capture object    vidin.release()    vidout.release()        # Closes all the frames    cv2.destroyWindow('OutputVideo')    def main(argv):    outputfile = './lane_finding_video.mp4' # default output file name    cameradata = 'cameradata.p'#    inputfile = './harder_challenge_video.mp4'#    inputfile = './challenge_video.mp4'    inputfile = './project_video.mp4'        try:        opts, args = getopt.getopt(argv,"hi:o:c:",                                   ["i=","o=","c="])    except getopt.GetoptError:        print("xxx.py -i <inputfile> -o <outputfile> -c <cameradata>")        sys.exit(2)    for opt, arg in opts:        if opt == '-h':            print("xxx.py -i <inputfile> -o <outputfile> -c <cameradata>")            sys.exit()        elif opt in ("-i", "--i"):            inputfile = arg        elif opt in ("-o", "--o"):            outputfile = arg        elif opt in ("-c", "--c"):            cameradata = arg    print("Input file is {}".format(inputfile))    print("Output file is {}".format(outputfile))    model(inputfile, outputfile, cameradata)if __name__ == "__main__":    main(sys.argv[1:])