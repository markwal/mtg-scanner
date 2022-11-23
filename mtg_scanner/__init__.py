import logging
logging.basicConfig(format='%(levelname)s\t%(message)s', level=logging.WARN)

import click
import cv2
from mtg_scanner import card
from mtg_scanner.scryfall import canonicalizeCard

@click.command()

@click.argument('image', nargs=-1, type=click.Path(exists=True))
@click.option('-o', '--output', type=click.File('w'), default='-')
@click.option('--debug/--nodebug', default=False)

def main(image, output, debug):
    logging.basicConfig(format='%(levelname)s\t%(message)s', 
            level=logging.INFO if debug else logging.WARN, force=True)
    logging.getLogger("root").setLevel(logging.DEBUG if debug else logging.WARN)
    for fn in image:
        logging.info(f'reading {fn}')
        try:
            img = cv2.imread(fn)
            if img is None:
                raise TypeError(f'Unable to read image file <{fn}>')
        except:
            logging.warn(f'Unable to read image <{fn}>')
            continue

        logging.info(f'recognizing {fn}')
        c = card.StraightCard(img, card_type=None, save_debug_images=debug)
        title = c.read_title(90)
        set_code = c.read_set_code()
        collector_number = c.read_collector_number()
        logging.info(f'Recognizer returned: {title} ({set_code}) {collector_number}')
        rval, cs = canonicalizeCard(title, set_code, collector_number)

        logging.info(f'Canonicalized: {rval}\t{cs}')
        print(f'{cs}', file=output)

if __name__ == '__main__':
    main()
