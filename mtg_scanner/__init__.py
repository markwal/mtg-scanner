import click
import cv2
from mtg_scanner import card
import logging

@click.command()

@click.argument('image', nargs=-1, type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path())
@click.option('--debug/--nodebug', default=False)

def main(image, output, debug):
    logging.basicConfig(format='%(levelname)s\t%(message)s', 
            level=logging.DEBUG if debug else logging.WARN)
    for fn in image:
        try:
            img = cv2.imread(fn)
            if img is None:
                raise TypeError(f'Unable to read image file <{fn}>')
        except:
            logging.warn(f'Unable to read image <{fn}>')
            continue

        c = card.StraightCard(img, card_type=None, save_debug_images=debug)
        print(f'filename:       {fn}')
#        print(f'read_title 120: {c.read_title(120)}')
        print(f'read_title 90:  {c.read_title(90)}')
        print(f'read_set_code:  {c.read_set_code()}')
        print(f'read_collector: {c.read_collector_number()}')

    if output:
        print(f'output filename: {output}')
        output.write("hello\n")

if __name__ == '__main__':
    main()
