import click
import cv2
from mtg_scanner import card
import logging

@click.command()

@click.argument('image', nargs=-1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.File('w'))

def main(image, output):
    logging.basicConfig(format='%(levelname)s\t%(message)s', level=logging.DEBUG)
    for fn in image:
        img = cv2.imread(fn)
        c = card.StraightCard(img, None, True)
#        print(f'read_title 120: {c.read_title(120)}')
        print(f'read_title 90: {c.read_title(90)}')
        print(f'read_set_code:  {c.read_set_code()}')
        print(f'read_collector: {c.read_collector_number()}')

    print(f'output filename: {output.name}')
    output.write("hello\n")

if __name__ == '__main__':
    main()
