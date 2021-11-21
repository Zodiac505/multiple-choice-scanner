# USAGE
# python test_grader.py --image images/test_01.png

# import the necessary packages
from imutils.perspective import four_point_transform
from imutils import contours
import numpy as np
import imutils
import cv2
import os
import tkinter as tk
from tkinter import filedialog


# Finding main border
def FindBorder():
        global paper
        global warped
        paper = image.copy()
        final_border = False
        first_time = True
        while final_border == False:
                # Converting image to grayscale, blur it slightly, and then finding edges
                gray = cv2.cvtColor(paper, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edged = cv2.Canny(blurred, 75, 200)

                # Find external contours, then checking the contour that corresponds to the border
                cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cnts = imutils.grab_contours(cnts)
                docCnt = None

                # ensure that at least one contour was found
                if len(cnts) > 0:
                        # sort the contours according to their size in descending order
                        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

                        # loop over the sorted contours
                        for c in cnts:
                                # approximate the contour
                                c = cv2.convexHull(c.copy())
                                peri = cv2.arcLength(c, True)
                                approx = cv2.approxPolyDP(c, 0.02 * peri, True)

                                # if our approximated contour has four points, and its area is more
                                # than half of the paper then we can assume we have found the paper
                                if (len(approx) == 4 and ((cv2.contourArea(approx) > gray.size * 0.5) or first_time)):
                                        docCnt = approx
                                        # apply a four point perspective transform to the original image
                                        paper = four_point_transform(paper.copy(), docCnt.reshape(4, 2))
                                        final_border = False
                                        break
                                else:
                                        final_border = True
                        first_time = False
                else:
                        print("Please input proper image")

        # grayscale image to obtain a top-down birds eye view of the paper
        warped = cv2.cvtColor(paper, cv2.COLOR_BGR2GRAY)



# finding all options
def FindOptions():
        global column
        global questionCnts
        global thresh
        
        # apply Otsu's thresholding method to binarize the warped piece of paper
        thresh = cv2.threshold(warped, 0, 255,cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        # find all contours in the thresholded image
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        # remove lines in between questions if there is any
        for (i,c) in enumerate(cnts):
                (x, y, w, h) = cv2.boundingRect(c)
                if w > thresh.shape[1]/5 or h > thresh.shape[0]/5:
                        thresh=cv2.drawContours(thresh,[c],-1,(0))

        # finding nearest w&h of questions
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        dic_wh = {}

        # investigating all contours to get w&h distribution dictionary 
        for c in cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                Key = str(w)+'-'+str(h)
                if w>5 and h>5:
                        if dic_wh.get(Key) is None:
                                dic_wh.update({Key:1})
                        else:
                                dic_wh[Key] = dic_wh.get(Key)+1

        # Finding most frequent w&h
        m = 0
        for k in dic_wh.keys():
                if m < dic_wh.get(k):
                        i = k.find('-')
                        m = dic_wh.get(k)
                        W = int(k[:i])
                        H = int(k[i+1:])

        # Finding question contours using obtained W & H
        questionCnts = []
        for c in cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                if w >= W*0.85 and w <= W*1.15 and h >= H*0.85 and h<= H*1.15:
                        questionCnts.append(c)

        # sorting and estimating missed questions
        questionCnts = list(contours.sort_contours(questionCnts,method="top-to-bottom")[0])
        x_list=[]
        y_list=[]
        x_count=[]
        y_count=[]

        for c in questionCnts[0:]:
                (x, y, w, h) = cv2.boundingRect(c)
                x_ok = 0
                y_ok = 0
                
                # checking x coordinate to find nearest column in x_list
                for i in range(0,len(x_list)):
                        if np.absolute(x-np.round_(x_list[i]/x_count[i])) < W:
                                x_list[i] = x_list[i] + x
                                x_count[i] = x_count[i] + 1
                                x_ok = 1
                                break
                if x_ok == 0:
                        x_list.append(x)
                        x_count.append(1)
                        
                # checking y coordinate to find nearest row in y_list
                for i in range(0,len(y_list)):
                        if np.absolute(y-np.round_(y_list[i]/y_count[i])) < H:
                                y_list[i] = y_list[i] + y
                                y_count[i] = y_count[i] + 1
                                y_ok = 1
                                break
                if y_ok == 0:
                        y_list.append(y)
                        y_count.append(1)

        # calculating average of row & columns coordinates
        for i in range(0,len(x_list)):
                x_list[i] = int(np.round_(x_list[i]/x_count[i]))
        for i in range(0,len(y_list)):
                y_list[i] = int(np.round_(y_list[i]/y_count[i]))

        # sorting row and column coordinates
        x_list.sort()
        y_list.sort()
        column = len(x_list)

        # sorting from left to right for each row considering number of founded questions
        index = 0
        for i in range(0,len(y_count)):
                questionCnts[index:index + y_count[i]] = list(contours.sort_contours(questionCnts[index:index + y_count[i]],method="left-to-right")[0])
                index = index + y_count[i]

        # inserting rectangle estimation of missed questions in proper position
        TheEnd = False
        for j in range(0,len(y_list)):
                for i in range(0,column):
                        if int(j*column+i) < len(questionCnts):
                                (x, y, w, h) = cv2.boundingRect(questionCnts[int(j*column+i)])
                        else:
                                TheEnd = True
                        if (np.absolute(x-x_list[i])>W or TheEnd):
                                temp_c = np.array([[[x_list[i],y_list[j]]],[[x_list[i],y_list[j]+H]],[[x_list[i]+W,y_list[j]+H]],[[x_list[i]+W,y_list[j]]],[[x_list[i],y_list[j]]]],np.int32)
                                questionCnts.insert(int(j*column+i),temp_c)



# finding correct answers
def CorrectingSheet():
        global paper
        global correct
        global column
        correct = 0
        question = 1

        while 1:
                # looping over each row considering number of columns
                for i in np.arange(0, len(questionCnts), column):
                        # Selecting all conours in one row
                        cnts = questionCnts[i:i + column]
                        bubbled=[]

                        # loop over the contours considering O_COUNT
                        for (j, c) in enumerate(cnts[0:O_COUNT]):
                                mask = np.zeros(thresh.shape, dtype="uint8")
                                # checking if the contour is estimated
                                if len(c) == 5:
                                        # calculating filled area
                                        cv2.drawContours(mask, [c], -1, 255, -1)
                                        total_area = cv2.countNonZero(mask)
                                        mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                                        total_colored = cv2.countNonZero(mask)
                                else:     
                                        # calculating filled area if contuor is not estimated
                                        ellipse = cv2.fitEllipse(c)
                                        cv2.ellipse(mask,ellipse,255,-1)
                                        total_area = cv2.countNonZero(mask)
                                        mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                                        total_colored = cv2.countNonZero(mask)
                                bubbled.append(total_colored/total_area)

                        # initialize the contour color and the index of the *correct* answer
                        Answer = 0
                        if (O_COUNT*max(bubbled)-sum(bubbled))/O_COUNT > 0.1:
                                Answer = bubbled.index(max(bubbled)) + 1
                        bubbled.pop(Answer-1)
                        if ((O_COUNT-1)*max(bubbled)-sum(bubbled))/(O_COUNT-1) > 0.1:
                                Answer = 0

                        # check to see if the bubbled answer is correct
                        color = (0, 0, 255)
                        k = ANSWER_KEY[question]
                        if Answer == k:
                                color = (0, 255, 0)
                                correct += 1

                        # draw the outline of the correct answer on the test
                        cv2.drawContours(paper, [cnts[k-1]], -1, color, 2)

                        # checking question count
                        question = question + 1
                        if question > Q_COUNT:
                                break

                if question > Q_COUNT:
                        break

                # checking if one column of questions is checked and removing related contours
                if column > O_COUNT:
                        for m in np.arange(len(questionCnts)-column, -1, column*(-1)):
                                for n in np.arange(0,O_COUNT):
                                        questionCnts.pop(m)
                        column = column - O_COUNT
                else:
                        break



# finding correct answers
def AnswerKey():
        global column
        global ANSWER_KEY
        
        question = 1

        while 1:
                # looping over each row considering number of columns
                for i in np.arange(0, len(questionCnts), column):
                        # Selecting all conours in one row
                        cnts = questionCnts[i:i + column]
                        bubbled=[]

                        # loop over the contours considering O_COUNT
                        for (j, c) in enumerate(cnts[0:O_COUNT]):
                                mask = np.zeros(thresh.shape, dtype="uint8")
                                # checking if the contour is estimated
                                if len(c) == 5:
                                        # calculating filled area
                                        cv2.drawContours(mask, [c], -1, 255, -1)
                                        total_area = cv2.countNonZero(mask)
                                        mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                                        total_colored = cv2.countNonZero(mask)
                                else:     
                                        # calculating filled area if contuor is not estimated
                                        ellipse = cv2.fitEllipse(c)
                                        cv2.ellipse(mask,ellipse,255,-1)
                                        total_area = cv2.countNonZero(mask)
                                        mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                                        total_colored = cv2.countNonZero(mask)
                                bubbled.append(total_colored/total_area)

                        # initialize the contour color and the index of the *correct* answer
                        Answer = 0
                        if (O_COUNT*max(bubbled)-sum(bubbled))/O_COUNT > 0.1:
                                Answer = bubbled.index(max(bubbled)) + 1
                        bubbled.pop(Answer-1)
                        if ((O_COUNT-1)*max(bubbled)-sum(bubbled))/(O_COUNT-1) > 0.1:
                                Answer = 0

                        # addig correct answer to the ANSWER_KEY
                        ANSWER_KEY.update({question:Answer})

                        # checking question count
                        question = question + 1
                        if question > Q_COUNT:
                                break

                if question > Q_COUNT:
                        break

                # checking if one column of questions is checked and removing related contours
                if column > O_COUNT:
                        for m in np.arange(len(questionCnts)-column, -1, column*(-1)):
                                for n in np.arange(0,O_COUNT):
                                        questionCnts.pop(m)
                        column = column - O_COUNT
                else:
                        break



# Getting required inputs
def GetInputs():
        global tempdir
        global Q_COUNT
        global O_COUNT
        global ANSWER_KEY
        global image
        print('*** Test sheet scanner ***')

        # Getting number of questions
        Q_COUNT = ''
        while type(Q_COUNT) == str:
                Q_COUNT = input('Enter number of questions:\n')
                try:
                        Q_COUNT = int(Q_COUNT)
                        print('\n')
                except ValueError:
                        print('\n!!! input should be positive integer !!!')

        # Getting number of options for each question
        O_COUNT = ''
        while type(O_COUNT) == str:
                O_COUNT = input('Enter number of options each question has:\n')
                try:
                        O_COUNT = int(O_COUNT)
                        print('\n')
                except ValueError:
                        print('!!! input should be positive integer !!!')

        # Identifying the method to get answer key
        methods = ['k', 'K', 'p', 'P']
        AKM = False
        while AKM == False:
                AnsK_Method = input('Choose the method to enter Answer Key: (k/p)\n** "k" for keyboard method and "p" for inputting a picture **\n')
                try:
                        if type(methods.index(AnsK_Method)) == int:
                                AKM = True
                except ValueError:
                        print('\n!!! input value not recognized !!!')

        # Getting answer key using keyboard method
        ANSWER_KEY ={}
        if AnsK_Method == 'k' or AnsK_Method == 'K':
                print('\n\n')
                i = 1
                while i <= Q_COUNT:
                        txt = 'Test #'+str(i)+':\t'
                        option = input(txt)
                        try:
                                option = int(option)
                                if option > 0 and option <= O_COUNT:
                                        ANSWER_KEY.update({i:option})
                                        i = i + 1
                                else:
                                        print('!!! not in range !!!')
                        except ValueError:
                                print('!!! input value not recognized !!!')
        else:
                # Getting answer key using picture method
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                currdir = os.getcwd()
                tempdir = filedialog.askopenfilename(parent=root, initialdir=currdir, title='Please select Answer Key')
                image = cv2.imread(tempdir)
                FindBorder()
                FindOptions()
                AnswerKey()

        # Printing inserted answer key
        print('\n\nAnswer Key inserted successfully')
        k = Q_COUNT/3
        k = int(np.floor(k/10-0.1)*10+10)
        for i in range(1,k+1):
                txt = ''
                for j in range(0,3):
                        if ANSWER_KEY.get(int(i+j*k)) is not None:
                                txt = txt + 'Test #' + str(int(i+j*k)) + ' : ' + str(ANSWER_KEY.get(int(i+j*k))) + '\t\t'
                print(txt)

        # Getting images which are to be processed 
        input('\n\nPress Enter to input test sheets ...')
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        currdir = os.getcwd()
        tempdir = filedialog.askopenfilenames(parent=root, initialdir=currdir, title='Please select test sheets')


# Main Program
GetInputs()
print('\n\n')
for sheetnumber in tempdir:
        image = cv2.imread(sheetnumber)
        FindBorder()
        cv2.imwrite(sheetnumber[:-4]+'_1.jpg',paper.copy())####
        FindOptions()
        cv2.imwrite(sheetnumber[:-4]+'_2.jpg',cv2.drawContours(paper.copy(),questionCnts,-1,(0,0,255),3))####        
        CorrectingSheet()
        cv2.imwrite(sheetnumber[:-4]+'_3.jpg',paper.copy())####
        # showing the result
        score = (correct / Q_COUNT) * 100
        sheetnumber = sheetnumber[sheetnumber.rfind('/')+1:sheetnumber.rfind('.')]
        txt1 = 'Score of "' + sheetnumber + '":\t{:.2f}%'.format(score)
        print(txt1)
        txt2 = 'Corrected Exam of "'+ sheetnumber +'"'
        cv2.namedWindow(txt2,cv2.WINDOW_NORMAL)
        cv2.imshow(txt2, paper)
input('Press Enter')
