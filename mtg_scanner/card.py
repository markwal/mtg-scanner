import numpy
import cv2
from sympy import Line, Line2D, Point
import pytesseract
import logging

# we're expecting a 88mm x 63mm card in the correct orientation
_mm_card_height = 88

# section rectangles are specified in mm
_title_section_rect = (2.5, 4, 45, 6)
_footer_line1_section_rect = (3, 82, 15, 2)
_footer_line2_section_rect = (3, 84, 15, 2)

_px_working_line_height = 185

# title dimensions in pixels within the cropped out section box
_title_left_margin = 45
_title_height = 77


class _StraightLine(object):
    def __init__(self, point, slope):
        self.line = Line(point, slope=slope)

    def get_y(self, x):
        (a, b, c) = self.line.coefficients
        return (a * x + c) / -b


class _TitleArea:
    def __init__(self, img, px_per_mm, left_margin, height, mid_line):
        self.img = img
        self.px_per_mm = px_per_mm
        self.left_margin = left_margin
        self.title_height = height
        self.mid_line = mid_line

    def bounding_rect(self):
        right = self.img.shape[1]
        return (int(self.left_margin), int(self.mid_line.get_y(self.left_margin) - self.title_height / 2),
            right - self.left_margin, int(self.mid_line.get_y(right) + self.title_height / 2))

    def px_from_mm(self, mm):
        return mm * self.px_per_mm


class _TitleFigureArea:
    def __init__(self, title_area, contour):
        self.title_area = title_area
        self.outer_contour = cv2.convexHull(contour)
        self.tight_contour = contour
        self.box = cv2.minAreaRect(contour)
        # FUTURE there's a bunch of nonsense in the heuristics relating to the fact
        # that the height and width of that minAreaRect aren't normalized to be
        # width along x-axis (ish) and height along y-axis (ish), probably
        # should normalize here and fix all the heuristics

    def __eq__(self, other):
        # if the outer contour is the same, close enough to not want to consider
        # separately
        if len(self.outer_contour) != len(other.outer_contour):
            return False

        for i in range(0, len(self.outer_contour)):
            if (self.outer_contour[i][0] != other.outer_contour[i][0]).any():
                return False

        return True

    
    def px_from_mm(self, mm):
        return self.title_area.px_from_mm(mm)


    def is_outside_title_area(self):
        ((x, y), (w, h), angle) = self.box
        x_approx = int(x - w / 2)
        y_mid_line = self.title_area.mid_line.get_y(x_approx)
        return x_approx < _title_left_margin or abs(y - y_mid_line) > _title_height / 2


    def is_i_dot(self):
        i_dot_height_max = self.px_from_mm(0.6)
        i_dot_height_min = self.px_from_mm(0.3)

        w, h = self.box[1]
        angle = self.box[2]

        return (h < i_dot_height_max and w < i_dot_height_max and h > i_dot_height_min and w > i_dot_height_min and \
            angle < -50 and angle > -40)


    def is_comma(self):
        ((x, y), (w, h), angle) = self.box
        if x < self.title_area.mid_line.get_y(x):
            return False

        h = max(w, h)
        return h < self.px_from_mm(1) and h > self.px_from_mm(0.2)


    def is_dot_like(self):
        return self.is_i_dot() or self.is_comma()


    def is_dash(self):
        ((x, y), (w, h), angle) = self.box

        # is it in the middleish
        y_mid = self.title_area.mid_line.get_y(x)
        if y < y_mid - _title_height / 5 or y > y_mid + _title_height / 5:
            return False

        if angle < -45:
            w, h = h, w

        # is it the shape of a dash
        if w == 0:
            return True
        aspect_ratio = h / w
        if aspect_ratio > 0.35 or aspect_ratio < 0.2:
            return False

        # is it the size-ish of a dash
        return h > self.px_from_mm(0.5) and h < self.px_from_mm(2) and \
            w > self.px_from_mm(0.5) and w < self.px_from_mm(2.5)


    def is_letter_sized(self):
        ((x, y), (w, h), angle) = self.box
        if w > h:
            w, h = h, w

        is_letter_sized = w > self.px_from_mm(0.1) and w < self.px_from_mm(4) and \
            h > self.px_from_mm(1.5) and h < self.px_from_mm(4)
        return is_letter_sized


    def is_noise(self):
        ((_, _), (w, h), _) = self.box
        if w > h:
            w, h = h, w
        
        if (h > self.px_from_mm(2)):
            logging.info(f'{self.is_dot_like()}, {self.is_dash()}, {self.is_letter_sized()}, {self.is_outside_title_area()}')

        return self.is_dot_like() or self.is_dash() or \
                not self.is_letter_sized() or self.is_outside_title_area()


    def is_contained_within(self, figure):
        # seems like this should be intersection of self and figure equivalent to self?
        # this approx logic is from CardReaderLibrary, perhaps the intersection method
        # is too slow?

        # if this center is outside the figure's convex hull then definitely not contained
        if cv2.pointPolygonTest(figure.outer_contour, self.box[0], False) <= 0:
            return False

        # if this center is inside and the area is smaller, good enough to discard
        return cv2.contourArea(self.outer_contour) < cv2.contourArea(figure.outer_contour)


    # if self is entirely contained in one of the other figures (except itself)
    # then we can throw it out
    def is_letter_hole(self, figures):
        # print("self is figure", list(map(lambda figure: self is figure, figures)))
        # return any(map(lambda figure: not self is figure and self.isContainedWithin(figure), figures))
        for figure in figures:
            if self.is_contained_within(figure):
                return True
        return False


def remove_dups_from_sorted(in_list):
    out_list = []

    if len(in_list) == 0:
        return out_list

    out_list.append(in_list[0])

    for item in in_list[1:]:
        if item != out_list[-1]:
            out_list.append(item)
        else:
            logging.info(f'skip item: {item.outer_contour}, out_list[-1]: {out_list[-1].outer_contour}')

    return out_list


# from CardReaderLibrary which says it is sorting by the left border, but this code ignores the rotation angle
# so it appears to either assume consistency from minAreaRect or doesn't care about the sort being that precise
def _FigureAreaSort(area):
    # RotatedRect ((center.x, center.y), (size.width, size.height), angle)
    return area.box[0][0] - min(area.box[1][0], area.box[1][1])



class StraightCard:
    def __init__(self, image, card_type, save_debug_images):
        self.image = image
        self.card_type = card_type
        self.save_debug_images = save_debug_images


    def _px_rect_from_mm(self, rect):
        (x, y, w, h) = rect
        (hpx, wpx, dcolors) = self.image.shape
        factor = hpx / _mm_card_height

        return (int(x * factor), int(y * factor), int(w * factor), int(h * factor))


    def _scale_section_rect(self, rect, size):
        (x, y, w, h) = rect   # rectangle in 0 to 1 coordinates
        (hpx, wpx, dcolors) = size     # pixel height and width of the total area

        return (int(x * wpx), int(y * hpx), int(w * wpx), int(h * hpx))  # section rect in pixel coordinates


    def _save_debug_image(self, fn, img):
        if self.save_debug_images:
            cv2.imwrite(fn, img)


    def _extract_and_prep_line(self, line_name, threshold, rect, invert=False):
        # crop the title title out
        x, y, w, h = self._px_rect_from_mm(rect)
        img = self.image[y:y+h, x:x+w].copy()
        logging.info(f'Extracted {line_name} dimensions: {img.shape}')
        self._save_debug_image(f'{line_name}-1-crop.png', img)

        # grayscale
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if invert:
            img = ~img
        self._save_debug_image(f'{line_name}-2-grayscale.png', img)

        # scale to working resolution
        h, w, *_ = img.shape
        img = cv2.resize(img, (int(w * _px_working_line_height / h), _px_working_line_height))
        logging.info(f'resized to {img.shape}, hoping for {_px_working_line_height}')
        self._save_debug_image(f'{line_name}-3-workingres.png', img)

        # blur image to smooth out scanning artifacts in the title background
        img = cv2.GaussianBlur(img, (3, 3), 0)
        self._save_debug_image(f'{line_name}-4-blurred.png', img)

        # threshold to monochrome
        ret, img = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        self._save_debug_image(f'{line_name}-5-threshold.png', img)

        return img


    def read_title(self, threshold):
        img = self._extract_and_prep_line("dbg-1-title", threshold, _title_section_rect)

        # find the letter contours
        edges = cv2.Canny(img, 120, 240, apertureSize=3)
        self._save_debug_image("dbg-2-canny.png", edges)
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) # back to color so we can draw on it

        # save the contours as a list of TitleFigureArea's and remove dups
        mid_line = _StraightLine(Point(0, _px_working_line_height/2), slope=0)  # REVIEW seems wrong
        px_per_mm = img.shape[0] / _title_section_rect[3] # extract height in pixels / height in mm
        logging.info(f'px_per_mm: {px_per_mm}, img height: {img.shape[0]}, img height in mm: {_title_section_rect[3]}')
        title_area = _TitleArea(img, px_per_mm, _title_left_margin, _title_height, mid_line)
        figures = list(map(lambda figure: _TitleFigureArea(title_area, figure), contours))
        logging.info(f'Detected {len(figures)} figures in the title area.')
        figures.sort(key = _FigureAreaSort)
        figures = remove_dups_from_sorted(figures)
        logging.info(f'After removing duplicates: {len(figures)}')

        # filter out the noisy contours
        figures = list(filter(lambda figure: not figure.is_noise(), figures))
        logging.info(f'After filtering noise: {len(figures)}')
        if len(figures) == 0:
            return ''
        contours = list(map(lambda figure: figure.outer_contour, figures))
        if self.save_debug_images:
            # draw the contours
            img_contours = cv2.drawContours(img.copy(), contours, -1, (0,0,255), 2)
            # draw the approximate bounding rectangle, FUTURE at midLine slope
            x, y, w, h = title_area.bounding_rect()
            img_contours = cv2.rectangle(img_contours, (x, y), (x + w, y + h), (0,255,0), 2)
            self._save_debug_image("dbg-3-contours.png", img_contours)

        # filter out the contours that are contained within the letters
        figures_in = figures
        figures = []
        for i in range(0, len(figures_in)):
            neighbors = figures[-1:]
            neighbors.extend(figures_in[i+1:i+2])
            if not figures_in[i].is_letter_hole(neighbors):
                figures.append(figures_in[i])
        figures_in = []
        logging.info(f'After filtering out interiors: {len(figures)}')

        # find the straight bounding rectangle of the figures we've found
        x, y, w, h = cv2.boundingRect(numpy.concatenate(contours))

        # draw the contours on an image and save the result
        contours = list(map(lambda figure: figure.outer_contour, figures))
        img_contours = cv2.drawContours(img.copy(), contours, -1, (255,0,255), 2)
        img_contours = cv2.rectangle(img_contours, (x, y), (x + w, y + h), (0,255,0), 2)
        self._save_debug_image("dbg-4-contours.png", img_contours)

        # Now that we've got the bounding box of the letters, crop it out
        img = img[y:y+h, x:x+w].copy()
        logging.info(f'tight crop dims: {img.shape}')
        self._save_debug_image("dbg-5-tight-crop.png", img)

        title = pytesseract.image_to_string(img, config=r'--psm 7')
        logging.info(f'card title: {title}')
        return title


    def read_set_code(self):
        img = self._extract_and_prep_line("dbg-6-set", 140, _footer_line2_section_rect, invert=True)
        set = pytesseract.image_to_string(img, config=r'--psm 7')
        logging.info(f'set: {set}')
        return set


    def read_collector_number(self):
        img = self._extract_and_prep_line("dbg-7-cnc", 140, _footer_line1_section_rect, invert=True)
        collector = pytesseract.image_to_string(img, config=r'--psm 7')
        logging.info(f'set: {set}')
        return collector
