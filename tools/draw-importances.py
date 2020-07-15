#!/usr/bin/env python3
import struct
import sys
import os
from os.path import splitext
import datetime
import numpy as np
from PIL import Image, ImageDraw
from matplotlib import pyplot as plt
import click
import glob
import re

@click.command()
@click.option('--path',  type = str,
        help = "Absolute File locations of extracted hres.png and imps.bin ")
@click.option('--input', help="Pass both hres.png and imps.bin",
                default=[None] * 2, type=click.Tuple([str, str]))

@click.option('--verbose', is_flag=True, help="Will print verbose messages.")
@click.option('--raw', is_flag=True, help="Print RAW Data of the bin.")


def blockImportance(input, verbose, path, raw):
    """
    CLI tool for extracting rav1e's Block Importance

    Renders block importances output by
    ContextInner::compute_lookahead_motion_vectors()
    ContextInner::compute_block_importances().

    Run rav1e binary with dump_lookahead_data feature flag to dump:\t\t
    For eg: `cargo run --features=dump_lookahead_data <input.y4m> -o /dev/null`

    Two modes available:\n
    Mode 1: Simple file, passing one hres.png, and one imps.bin \t\t
    Mode 2: Batch file processing for multiple hres and imps data\n
    Output files will be saved in out/YYYYMMDD_HH folder in -imps.png files.

    """

    if input == (None, None) and path == None :
        raise click.BadParameter("Please use either --input or --path method, for more information use --help.")

    if verbose:
        click.echo("Input given: "+ str(input))
        click.echo("Path given: " + str(path))

    if input != (None, None):
        if verbose:
            click.secho("MODE 1", fg="yellow")
        with open(input[1], 'rb') as f:
            contents = f.read()

        rows, cols = struct.unpack('qq', contents[:16])
        imps = np.frombuffer(contents[16:],
                            dtype=np.float32).reshape((rows, cols))

        if raw:
            click.secho("imps data after processing:", fg="red")
            click.echo(imps)

    elif path != None:
        if verbose:
            click.secho("MODE 2", fg="yellow")
        bin_list = []
        imps_list = []
        rows_list = []
        col_list = []
        png_list = glob.glob(str(path)+"/*hres.png")
        for png_iter in png_list:
             bin_list.append(png_iter.replace("hres.png","imps.bin"))
        total_files = len(bin_list)

        for bin in bin_list:
            with open(bin, 'rb') as f:
                contents_batch = (f.read())
                rows, cols, = struct.unpack('qq', contents_batch[:16])
                imps = np.frombuffer(contents_batch[16:],
                                    dtype=np.float32).reshape((rows, cols))
                imps_list.append(imps)
                rows_list.append(rows)
                col_list.append(cols)

        if raw:
            click.secho("The full imps data after processing:", fg="red")
            click.echo(imps_list)

    if verbose and path != None:
        click.secho("\n png list: "+ str(png_list), fg="green")
        click.secho("\n bin list: "+ str(bin_list), fg="red")
        click.secho("\n Total Count: "+ str(total_files))

    # Use a fixed scale where anything >= 10 cannot be distinguished
    # to allow visually comparing multiple pictures
    max_imp = 10 ## Replace by `np.max(imps)` for relative scaling
    fig_list = []
    frame_size_multiplier = 4
    mv_original_block_size = 8 // 2 # The importances are in 8×8 blocks, but we use half-resolution images.
    mv_block_size = mv_original_block_size * frame_size_multiplier
    folder_path = "out/"+ datetime.datetime.now().strftime('%Y%m%d_%H')

    if not os.path.exists('out'):
        os.mkdir('out')

    if not os.path.exists(folder_path):
        os.mkdir(folder_path)

    if path == None:
        frame = Image.open(input[0])
        frame = frame.resize((frame.width * frame_size_multiplier,
                                        frame.height * frame_size_multiplier))
        frame = frame.convert(mode='RGB')
        draw = ImageDraw.Draw(frame, mode='RGBA')

         # Draw the grid.
        for i in range(0, frame.width, mv_block_size):
             draw.line(((i, 0), (i, frame.height)), fill=(0, 0, 0, 255))
        for i in range(0, frame.height, mv_block_size):
            draw.line(((0, i), (frame.width, i)), fill=(0, 0, 0, 255))

        # Draw the importances.
        if max_imp > 0:
            for y in range(rows):
                for x in range(cols):
                    imp = imps[y, x]
                    top_left = (x * mv_block_size, y * mv_block_size)
                    bottom_right = (top_left[0] + mv_block_size, top_left[1]
                                                            + mv_block_size)
                    draw.rectangle((top_left, bottom_right), fill=(int(imp /
                                                    max_imp * 255), 0, 0, 128))

        fig = plt.figure(figsize=(frame.width, frame.height), dpi=1)
        fig.figimage(frame, cmap='gray')
        plt.savefig(folder_path+'/'+ splitext(os.path.basename(input[1]))[0] + '.png',
                                                    bbox_inches='tight')

    else:
        for (png_batch, bin_batch, imps_batch, rows_batch, cols_batch) in  zip(
                   png_list, bin_list, imps_list, rows_list, col_list):
            frame_batch = Image.open(png_batch)
            frame_batch = frame_batch.resize((frame_batch.width *
             frame_size_multiplier, frame_batch.height * frame_size_multiplier))
            frame_batch = frame_batch.convert(mode='RGB')
            draw = ImageDraw.Draw(frame_batch, mode='RGBA')

            # Draw the grid.
            for i in range(0, frame_batch.width, mv_block_size):
                 draw.line(((i, 0), (i, frame_batch.height)), fill=(0, 0, 0, 255))
            for i in range(0, frame_batch.height, mv_block_size):
                draw.line(((0, i), (frame_batch.width, i)), fill=(0, 0, 0, 255))

            # Draw the importances.
            if max_imp > 0:
                for y in range(rows_batch):
                    for x in range(cols_batch):
                        imp = imps_batch[y, x]
                        top_left = (x * mv_block_size, y * mv_block_size)
                        bottom_right = (top_left[0] + mv_block_size, top_left[1]
                                                            + mv_block_size)
                        draw.rectangle((top_left, bottom_right), fill=(int(imp
                                                  / max_imp * 255), 0, 0, 128))

            fig = plt.figure(figsize=(frame_batch.width, frame_batch.height),
                                                                dpi=1)
            fig.figimage(frame_batch, cmap='gray')
            plt.savefig(folder_path + '/' + splitext(os.path.basename(bin_batch))[0]
                            + ".png", bbox_inches='tight')
            if verbose:
                click.secho(str(folder_path + '/'+
                        splitext(os.path.basename(bin_batch))[0] +".png"), fg="blue")


    if raw:
        click.secho("List of Figure Elements: "+str(fig_list))

    if verbose:
        if path == None:
            click.secho("File name is "+ splitext(input[1])[0]+ ".png",
                                                            fg="blue")
        print("Folder Path: "+ os.getcwd()+"/"+ folder_path)

    click.secho("Processing done.", fg="green")

if __name__ == "__main__":
    blockImportance()

