import click
import io

@click.command()

@click.argument('image', nargs=-1, type=click.File('rb'))
@click.argument('output', nargs=1, type=click.File('w'))

def main(image, output):
    for fn in image:
        chunk = fn.read(1024)
    print(f'output filename: {output.name}')
    output.write("hello\n")

if __name__ == '__main__':
    main()
