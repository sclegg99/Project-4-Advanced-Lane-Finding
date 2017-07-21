#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 13:45:18 2017

@author: sclegg

Calibration code reference:
    http://docs.opencv.org/3.1.0/dc/dbb/tutorial_py_calibration.html 
"""

import numpy as np
import cv2
import glob
import sys, getopt
import matplotlib.pyplot as plt
import pickle

# unwarp the image to create a birds-eye view
# given the source and destination points of the
# image
def corners_unwarp(img, img_size, corners, nx, dst):
        
    # define src corners
    src = np.float32([corners[0], corners[nx-1], corners[-1], corners[-nx]])
    
    # create perspective transformation matrix
    M = cv2.getPerspectiveTransform(src, dst)
    
    # warp image
    warped = cv2.warpPerspective(img, M, img_size, flags=cv2.INTER_LINEAR)
        
    return warped, M


# undistort the img image give the camera
# matrix and distortion coefficients
def un_distort(img, mtx, dist):
    h,  w = img.shape[:2]
    newcameramtx, roi=cv2.getOptimalNewCameraMatrix(mtx,dist,(w,h),1,(w,h))
    
    # undistort
    dst = cv2.undistort(img, mtx, dist, None, newcameramtx)

    # crop the image
    x,y,w,h = roi
    dst = dst[y:y+h, x:x+w]
    return dst

def montage(X):
# Help function to plot an array of images
# as a montage.
    count, n, m, depth = np.shape(X)
    nn = int(np.ceil(np.sqrt(count)))
    mm = nn
    M = np.zeros((nn * n, mm * m, depth))
    image_id = 0
    for j in range(nn):
        for k in range(mm):
            if image_id >= count: 
                break
            sliceN, sliceM = j * n, k * m
            image = X[image_id]
            M[sliceN:sliceN+n, sliceM:sliceM+m] = image.astype(float)
            image_id += 1
    return M


def calibrate(directory, extension, outputfilename, nrows, ncols):
    # termination criteria for the subpixel routine
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((nrows*ncols,3), np.float32)
    objp[:,:2] = np.mgrid[0:nrows,0:ncols].T.reshape(-1,2)

    # Arrays to store object points and image points from all the images.
    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.
    
    # Array to store images
    images = [] # 4d array of images
    image_shape = (720, 1280, 3) # Expected image shape
    img_size = (image_shape[1], image_shape[0])
    
    # Array to store corner points for each image
    image_corners = []

    # Get list of images in directory    
    image_files = directory + extension
    image_names = glob.glob(image_files)
 
    for fname in image_names:
        print("read image {}".format(fname))
        img = cv2.imread(fname)
        if np.array(img).shape != image_shape:
            print("Wrong image shape--skipping")
            continue

        # Convert image from RBG to gray
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    
        # Find the chess board corners
        ret, corners = cv2.findChessboardCorners(gray, (nrows, ncols), None)
    
        # If found, add object points, image points (after refining them)
        if ret == True:
            objpoints.append(objp)
            
            cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
            imgpoints.append(corners)
        
            # Draw and display the corners
            cv2.drawChessboardCorners(img, (nrows, ncols), corners, ret)
            
            # Append images for subsequent plotting
            images.append(img)
            image_corners.append(corners)

    # Plot montage of checkerboard images with corners plotted
    images = np.array(images)
    image_corners = np.array(image_corners)
    plot = montage(images)

    # Calibrate
    print("calibrate camera")
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints,
                                                   imgpoints,
                                                   gray.shape[::-1],
                                                   None, None)
   
    text_file = open(outputfilename+'.txt', 'w')
    text_file.write("*******************\n")
    text_file.write("Camera matrix:\n")
    for i in range(3):
        text_file.write(" {} {} {}\n".format(mtx[i][0],
                        mtx[i][1],mtx[i][2]))
    text_file.write("\n*******************\n")
    text_file.write("Lens distortion coefficients:\n")
    text_file.write("r1: {}\n".format(dist[0][0]))
    text_file.write("r2: {}\n".format(dist[0][1]))
    text_file.write("r3: {}\n".format(dist[0][4]))
    text_file.write("t1: {}\n".format(dist[0][2]))
    text_file.write("t1: {}\n".format(dist[0][3]))
    text_file.write("\n*******************\n")

    print("*******************")
    print("camera matrix is {}".format(mtx))
    print("*******************")
    print("distortion coefficients are {}".format(dist))
    print("*******************")
    
    camera_pickle= {"mtx":mtx, "dist":dist}
    pickle.dump(camera_pickle, open( outputfilename+'.p', 'wb' ) )
    print("dumped pickle file")

    # undistore and unwarp images
    # create empty list to hold unwarped images
    undst = []
    
    # define destination corners
    offset = 100 # offset for dst points
    dest = np.float32([[offset, offset], [img_size[0]-offset, offset],
                      [img_size[0]-offset, img_size[1]-offset],
                      [offset, img_size[1]-offset]])

    for img, corners in zip(images, image_corners):
        dst = un_distort(img, mtx, dist)
        dst, M = corners_unwarp(dst, img_size, corners, nrows, dest)
        undst.append(dst)
        
    undst = np.array(undst)
    plot_undst = montage(undst)

    f, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3))
    f.tight_layout()
    ax1.set_axis_off()
    ax1.imshow(plot)
    ax1.set_title('Original Image', fontsize=20)
    ax2.set_axis_off()
    ax2.imshow(plot_undst)
    ax2.set_title('Undistorted Image', fontsize=20)
    plt.subplots_adjust(left=0., right=1, top=0.9, bottom=0.)
    f.savefig('checkboard_montage.png')

    l2 = np.empty(0)
    for i in range(len(objpoints)):
        
        # compute reprojection of objection points
        imgpoints2, _ = cv2.projectPoints(objpoints[i],
                                          rvecs[i], tvecs[i], mtx, dist)
        
        # compute l2 norm of the difference between the 
        # corner points and their reprojections
        l22 = np.linalg.norm(np.reshape(np.array(imgpoints[i]-imgpoints2),
                          (nrows*ncols,2)),axis=1)

        l2 = np.append(l2, l22)
    
    # Take square root of l2
    l2 = np.sqrt(l2)
    
    # Calcuate mean and standard deviation of l2
    mean_error = np.mean(l2)
    std_error = np.std(l2)
    
    text_file.write("                 Mean reprojection error: {}\n"
                    .format(mean_error))
    text_file.write("Standard deviation of reprojection error: {}\n"
                    .format(std_error))    

    print("                 Mean reprojection error: {}".format(mean_error))
    print("Standard deviation of reprojection error: {}".format(std_error))    
    text_file.close()
    
def main(argv):
    directory = './camera_cal/' # default director for calibraiton images
    extension = '*.jpg'         # default image file extension
    outputfile = 'cameradata' # default output file name
    nrows = 9                   # default number of checkerboard rows
    ncols = 6                   # default number of checkerboard columns
    
    try:
        opts, args = getopt.getopt(argv,"hd:e:o:r:c:",
                                   ["d=","e=","o=","r=","c="])
    except getopt.GetoptError:
        print("test.py -d <directory> -e <extension> -o <outputfile> -r rows -c cols")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("test.py -d <directory> -e <extension> -o <outputfile>")
            sys.exit()
        elif opt in ("-d", "--d"):
            directory = arg
        elif opt in ("-e", "--e"):
            extension = arg
        elif opt in ("-o", "--o"):
            outputfile = arg
        elif opt in ("-r", "--r"):
            nrows = int(arg)
        elif opt in ("-c", "--c"):
            ncols = int(arg)
    print("Directory file is {}".format(directory))
    print("Extension is {}".format(extension))
    print("Output file is {}".format(outputfile))
    calibrate(directory, extension, outputfile, nrows, ncols)

if __name__ == "__main__":
    main(sys.argv[1:])