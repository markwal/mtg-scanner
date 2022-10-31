import numpy
import cv2
from sympy import Line, Line2D, Point
import pytesseract

# we're expecting a 88mm x 63mm card in the correct orientation
_mmCardHeight = 88

# section rectangles are specified in mm
_titleSectionRect = (2.3, 4, 39.5, 6)
_footerLine1SectionRect = (3, 82, 15, 6)
_footerLine2SectionRect = (3, 88, 15, 6)

_pxWorkingLineHeight = 185

# title dimensions in pixels within the cropped out section box
_titleLeftMargin = 45
_titleRightMargin = 1685
_titleHeight = 77


class StraightLine(object):
    def __init__(self, point, slope):
        self.line = Line(point, slope=slope)

    def getY(self, x):
        (a, b, c) = self.line.coefficients
        return (a * x + c) / -b


class FigureArea:
    def __init__(self, contour):
        self.outerContour = cv2.convexHull(contour)
        self.tightContour = contour
        self.box = cv2.minAreaRect(contour)
        # FUTURE there's a bunch of nonsense in the heuristics relating to the fact
        # that the height and width of that minAreaRect aren't normalized to be
        # width along x-axis (ish) and height along y-axis (ish), probably
        # should normalize here and fix all the heuristics

    def __eq__(self, other):
        # if the outer contour is the same, close enough to not want to consider
        # separately
        if len(self.outerContour) != len(other.outerContour):
            return False

        for i in range(0, len(self.outerContour)):
            if not (self.outerContour[i][0] == other.outerContour[i][0]).all():
                return False

        return True

    def isOutsideTitleArea(self, titleMidLine):
        ((x, y), (w, h), angle) = self.box
        xApprox = int(x - w / 2)
        yMidLine = titleMidLine.getY(xApprox)
        return xApprox < workingTitleLeftMargin or xApprox > workingTitleRightMargin or \
            abs(self.box[0][1] - yMidLine) > workingTitleHeight / 2

    def isIDot(self):
        iDotMax = workingCardHeight / 34
        iDotMin = workingCardHeight / 68

        w, h = self.box[1]
        angle = self.box[2]

        return (h < iDotMax and w < iDotMax and h > iDotMin and w > iDotMin and \
            angle < -50 and angle > -40)


    def isComma(self, titleMidLine):
        ((x, y), (w, h), angle) = self.box
        if x < titleMidLine.getY(x):
            return False

        h = max(w, h)
        return h < workingCardHeight / 20 and h > workingCardHeight / 34


    def isDotLike(self, titleMidLine):
        return self.isIDot() or self.isComma(titleMidLine)


    def isDash(self, titleMidLine):
        ((x, y), (w, h), angle) = self.box

        # is it in the middleish
        yMid = titleMidLine.getY(x)
        if y < yMid - workingTitleHeight / 5 or y > yMid + workingTitleHeight / 5:
            return False

        if angle < -45:
            w, h = h, w

        # is it the shape of a dash
        if w == 0:
            return True
        aspectRatio = h / w
        if aspectRatio > 0.35 or aspectRatio < 0.2:
            return False

        # is it the size-ish of a dash
        return h > workingCardHeight / 170 and h < workingCardHeight / 42.5 and \
            w > workingCardHeight / 34 and w < workingCardHeight / 8.5


    def isLetterSized(self):
        ((x, y), (w, h), angle) = self.box
        if w > h:
            w, h = h, w

        return w > workingCardHeight / 52.3 and w < workingCardHeight / 5.9 and \
            h > workingCardHeight / 22.65 and h < workingCardHeight / 5.9


    def isNoise(self, titleMidLine):
        return self.isDotLike(titleMidLine) or self.isDash(titleMidLine) or \
                not self.isLetterSized() or self.isOutsideTitleArea(titleMidLine)


    def isContainedWithin(self, figure):
        # seems like this should be intersection of self and figure equivalent to self?
        # this approx logic is from CardReaderLibrary, perhaps the intersection method
        # is too slow?

        # if this center is outside the figure's convex hull then definitely not contained
        if cv2.pointPolygonTest(figure.outerContour, self.box[0], False) <= 0:
            return False

        # if this center is inside and the area is smaller, good enough to discard
        return cv2.contourArea(self.outerContour) < cv2.contourArea(figure.outerContour)


    # if self is entirely contained in one of the other figures (except itself)
    # then we can throw it out
    def isLetterHole(self, figures):
        # print("self is figure", list(map(lambda figure: self is figure, figures)))
        # return any(map(lambda figure: not self is figure and self.isContainedWithin(figure), figures))
        for figure in figures:
            if self.isContainedWithin(figure):
                return True
        return False


def _RemoveDuplicatesFromSorted(inList):
    outList = []

    if len(inList) == 0:
        return outList

    outList.append(inList[0])

    for item in inList[1:]:
        if item != outList[-1]:
            outList.append(item)
        else:
            print("item: ", item.outerContour)
            print("outList[-1]: ", outList[-1].outerContour)
            print("skip")

    return outList


# from CardReaderLibrary which says it is sorting by the left border, but this code ignores the rotation angle
# so it appears to either assume consistency from minAreaRect or doesn't care about the sort being that precise
def _FigureAreaSort(area):
    # RotatedRect ((center.x, center.y), (size.width, size.height), angle)
    return area.box[0][0] - min(area.box[1][0], area.box[1][1])



class StraightCard:
    def __init__(self, image, cardType):
        self.image = image
        self.cardType = cardType


    def _PxRectFromMm(self, rect):
        (x, y, w, h) = rect
        (hpx, wpx, dcolors) = self.image.shape
        factor = hpx / _mmCardHeight

        return (int(x * factor), int(y * factor), int(w * factor), int(h * factor))


    def _ScaleSectionRect(self, rect, size):
        (x, y, w, h) = rect   # rectangle in 0 to 1 coordinates
        (hpx, wpx, dcolors) = size     # pixel height and width of the total area

        return (int(x * wpx), int(y * hpx), int(w * wpx), int(h * hpx))  # section rect in pixel coordinates


    def _GetNormalTitleSectionRect(self, size):
        return self._ScaleSectionRect((0.037, 0.045, 0.62839, 0.068), size)


    def ReadTitle(self, threshold):
        # crop the title title out
        x, y, w, h = self._PxRectFromMm(_titleSectionRect)
        img = self.image[y:y+h, x:x+w].copy()
        print('crop dims:', img.shape)
        cv2.imwrite("test-1-crop.png", img)

        # grayscale
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imwrite("test-2-grayscale.png", img)

        # scale to working resolution
        w, h, d = img.shape
        img = cv2.resize(img, (int(h * _pxWorkingLineHeight / w), _pxWorkingLineHeight))
        cv2.imwrite("test-3-workingres.png", img)

        # blur image to smooth out scanning artifacts in the title background
        img = cv2.GaussianBlur(img, (3, 3), 0)
        cv2.imwrite("test-4-blurred.png", img)

        # threshold to monochrome
        ret, img = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        cv2.imwrite("test-5-threshold.png", img)

        # find the letter contours
        edges = cv2.Canny(img, 120, 240, apertureSize=3)
        cv2.imwrite("test-6-canny.png", edges)
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) # back to color so we can draw on it

        # save the contours as a list of FirgureArea's and remove dups
        figures = list(map(lambda figure: FigureArea(figure), contours))
        print("# of figures: ", len(figures))
        figures.sort(key = _FigureAreaSort)
        figures = _RemoveDuplicatesFromSorted(figures)
        print("# of figures after remove dups: ", len(figures))

        # filter out the noisy contours
        baseLine = midLine = StraightLine(Point(0, workingTitleHeight), slope=0)
        figures = list(filter(lambda figure: not figure.isNoise(midLine), figures))
        print("# of figures after noise filter: ", len(figures))
        contours = list(map(lambda figure: figure.outerContour, figures))
        imgContours = cv2.drawContours(img.copy(), contours, -1, (0,0,255), 2)
        imgContours = cv2.rectangle(imgContours, 
            (int(workingTitleLeftMargin), int(midLine.getY(workingTitleLeftMargin) - workingTitleHeight / 2)),
            (int(workingTitleRightMargin), int(midLine.getY(workingTitleRightMargin) + workingTitleHeight / 2)),
            (0,255,0), 2)
        cv2.imwrite("test-7-contours.png", imgContours)

        # filter out the contours that are contained within the letters
        figuresIn = figures
        figures = []
        for i in range(0, len(figuresIn)):
            neighbors = figures[-1:]
            neighbors.extend(figuresIn[i+1:i+2])
            if not figuresIn[i].isLetterHole(neighbors):
                figures.append(figuresIn[i])
        figuresIn = []
        print("# of figures after hole filter: ", len(figures))

        # find the straight bounding rectangle of the figures we've found
        x, y, w, h = cv2.boundingRect(numpy.concatenate(contours))

        # draw the contours on an image and save the result
        contours = list(map(lambda figure: figure.outerContour, figures))
        imgContours = cv2.drawContours(img.copy(), contours, -1, (255,0,255), 2)
        imgContours = cv2.rectangle(imgContours, (x, y), (x + w, y + h), (0,255,0), 2)
        cv2.imwrite("test-8-contours.png", imgContours)

        # Now that we've got the bounding box of the letters, crop it out
        img = img[y:y+h, x:x+w].copy()
        print('tight crop dims:', img.shape)
        cv2.imwrite("test-9-tight-crop.png", img)

        title = pytesseract.image_to_string(img, config=r'--psm 7')
        print("card title: ", title)


    def readSetAndCardNumber(self):
        # grab the original image and scale it down to working rez
        img = cv2.resize(inImage, (int(workingFooterCardHeight * inImage.shape[1] / inImage.shape[0]), workingFooterCardHeight))

        # crop out the footer section
        x = workingFooterLeftMargin
        y = workingFooterTopMargin
        img = img[y:y+workingFooterCropHeight, x:x+workingFooterCropWidth].copy()
        cv2.imwrite("test-footer-1-crop.png", img)

        # grayscale then threshold
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = ~img
        img = cv2.GaussianBlur(img, (3, 3), 0)
        cv2.imwrite("test-footer-2-invert.png", img)
        ret,img = cv2.threshold(img, 140, 255, cv2.THRESH_BINARY)
        cv2.imwrite("test-footer-3-threshold.png", img)

image = cv2.imread("test.png")
print('dimensions', image.shape)
ReadTitleOfStraightCard(image, 120, 1)

