from PIL import Image
import os
import argparse
import sys

def scale_crop(v:int, scale=256) -> int:
    """scale input v and crop it in  range 0 .. 255

    Args:
        v (int): input value
        scale (int, optional): scale factor. Defaults to 256.

    Returns:
        int: result of scale and crop
    """
    v = (v + scale - 1) // scale
    if(v < 0):
        return 0
    elif(v > 255):
        return 255
    return v

def rgba2rgb(c, bg=[255, 255, 255]):
    """Convert RGBA (0..255) to RGB (0..255) with known background, with scale and crop

    Args:
        c (list): input RGBA color array[0..3] 
        bg (list, optional): background color. Defaults to [255, 255, 255].

    Returns:
        list: RGB 
    """
    r = c[0]
    g = c[1]
    b = c[2]
    alpha = c[3]

    bg_r = bg[0]
    bg_g = bg[1]
    bg_b = bg[2]
    return [scale_crop((255 - alpha) * bg_r + alpha * r),\
        scale_crop((255 - alpha) * bg_g + alpha * g),\
        scale_crop((255 - alpha) * bg_b + alpha * b)]

def color_invert(c):
    """Invert color RGB (0..255)

    Args:
        c (list): input RGB color 

    Returns:
        list: RGB color
    """
    return [255 - c[0], 255 - c[1], 255 - c[2]]

    
def get_y(rgb) -> int:
    """Calculate Y (luma) from RGB

    Args:
        rgb (list): RGB color (0..255)

    Returns:
        int: Y (0..255)
    """
    return scale_crop(76 * rgb[0] + 150 * rgb[1] + 29 * rgb[2])

def get_h_define(filename:str) -> str:
    """Get define base name from input image filename

    Args:
        filename (str): input image filename 

    Returns:
        str: define base name 
    """
    base=os.path.basename(filename)
    f = os.path.splitext(base)
    
    return "IMG_" + str(f[0]).replace("-", "_")


def get_h_filename(filename:str) -> str:
    """Get header filename fro input image filename 

    Args:
        filename (str): input image filename 

    Returns:
        str: header filename 
    """
    base=os.path.basename(filename)
    f = os.path.splitext(base)
    ext = str(f[1]).replace(".", "")
    return "Img_" + f[0] + "_" + ext + ".h", f[0]

def save_to_h(filename:str, result:list, w:int, h:int, items_per_row:int=8, comments:str="", flags:int=0x0, output_folder:str="."):
    """Create header with image and defines 

    Args:
        filename (str): input image file name, the header name will be generated 
        result (list): array with pixels 
        w (int): result image width in pixels
        h (int): result image height in pixels 
        items_per_row (int, optional): items per row in destination array, just for nice view. Defaults to 8.
        comments (str, optional): comments section in header. Defaults to "".
        flags (int, optional): image flags, reserved for future. Defaults to 0x0.
        output_folder (str, optional): output folder. Defaults to ".".

    Returns:
        _type_: _description_
    """
    hf, fn_only = get_h_filename(filename)
    f = open(os.path.join(output_folder, hf), "wt")
    def_base = get_h_define(filename)
    f.write("#ifndef " + def_base + "\n")
    f.write("#define " + def_base + "\n\n\n")
    s_w = def_base + "_W"
    s_h = def_base + "_H" 
    s_fn = def_base + "_FILENAME"
    s_d = def_base + "_Data"
    s_fl = def_base + "_FLAGS"
    s_d_l = def_base + "_DATA_LEN"
    f.write("#define " + s_w + "\t" + str(w) + "\n")
    f.write("#define " + s_h + "\t" + str(h) + "\n")
    f.write("#define " + s_fl + "\t" + str(flags) + "\n")
    f.write("#define " + s_fn  + "\t" + "\""  + str(fn_only) + "\"\n")
    f.write("#define " + s_d_l + "\t" + str(len(result)) + "\n")

    if(comments != ""):
        f.write("/*\n" + comments + "*/\n\n")

    f.write("static const unsigned char " + s_d + "[] = { \n")

    idx = 0
    gidx = 0
    s = ""
    for r in result:
        if(idx == 0):
            start = gidx
            s += "\t"
        s += hex(r) + ", "
        idx += 1
        gidx += 1
        if(idx == items_per_row):
            s += "//" + str(start) + "\n"
            idx = 0
    if(idx > 0):
        s += "//" + str(start) + "\n"
    
    f.write(s)
    
    f.write("};// " + def_base + "_Data[]\n\n\n")
    f.write("#endif //" + def_base + "\n")

    f.close()
    return (hf, s_w, s_h, s_fl, s_d, s_fn)

def main(filename:str, list_include:str="", list_struct:str="", output_folder:str=".", dest_w:int=16, dest_h:int=16, thr:int=127):
    """Main function, it converts input image (RGB/RGBA) to SSD1306 format
    Let assume we have an image
     01234567              
    0*
    1  *
    2    *
    3      *
    4 *
    5   *
    6     *
    7       *

    Because SSD1306 prints it by 8 x 1bpp pixels in column, the desination array is 
    0x01, 0x10, 0x02, 0x20, 0x04, 0x40, 0x08, 0x80

    The conversion happens by window scale_y x scale_x,. For each pixel
    1. [optional] convert RGBA to RGB
    2. Get Y (luma) for each pixel 
    3. Calculate average Y luma
    4. If it is > threshold, the destination pixels = 1 

    In addition two files are written in **append** mode:
    1. list_include with string "#include "<header file name.h>"
    2. list_struct with struct record in format 
       {width, height, flags, data, image filename}

        The struct type definition is
        ================================
        typedef uint8_t SSD1306_Image_Geometry_t;
        typedef uint8_t SSD1306_Image_Flags_t;
        typedef unsigned char SSD1306_Image_Data_t;

        struct tag_ImageData
        {
            SSD1306_Image_Geometry_t w;
            SSD1306_Image_Geometry_t h;
            SSD1306_Image_Flags_t fl;
            const SSD1306_Image_Data_t * data;
            const char * filename;
        };

        typedef struct tag_ImageData ImageData;
        ================================

        Usage for that files: 
        1. In global space in C/C++ file
            #include "inc_imgs.h"
            
            const ImageData images[] = {
                #include "inc_struct.h"
            };
        2. Somewhere in function (like main) in C/C++ file
            const size_t images_count = sizeof(images) / sizeof(images[0]);
            size_t idx = 0;
            while(1)
            {
                ssd1306_draw_image(0, 32, images[idx].w, images[idx].h, images[idx].data);
                Delay_Ms(SLIDE_SHOW_DELAY);
                idx = (idx + 1) % images_count;
            }




    Args:
        filename (str): input image filename 
        list_include (str, optional): file for includes (append). Defaults to "".
        list_struct (str, optional): file for struct (append). Defaults to "".
        output_folder (str, optional): output folder for all files. Defaults to ".".
        dest_w (int, optional): destination image width. Defaults to 16.
        dest_h (int, optional): destination image height. Defaults to 16.
        thr (int, optional): pixel threshold. Defaults to 127.
    """

    # creating a image object
    comments = ""
    im = Image.open(filename)
    comments += "Filename: " + filename + "\n"
    px = im.load()
    h = im.height
    w = im.width
    
    comments += "Input image Width: " + str(w) + "\n"
    comments += "Input image Height: " + str(h) + "\n"

    scale_factor_x = (w) // dest_w
    if(scale_factor_x < 1):
        scale_factor_x = 1


    scale_factor_y = (h) // dest_h
    if(scale_factor_y < 1):
        scale_factor_y = 1

    comments += "Scale factor X: " + str(scale_factor_x) + "\n"
    comments += "Scale factor Y: " + str(scale_factor_y) + "\n"
    hn = h // scale_factor_y
    hn2 = (hn + 8 - 1) // 8
    wn = w // scale_factor_x

    if((hn != dest_h) or (wn != dest_w)):
        exit("ERROR Exit! Cannot find good scale factor:\n" \
            + "Scale factor X: " + str(scale_factor_x) + "\n" \
            + "Scale factor Y: " + str(scale_factor_y) + "\n" \
            + "Result image Width: " + str(wn) + " but expected " + str(dest_w) + "\n" \
            + "Result image Height: " + str(hn) + " but expected " + str(dest_h) + "\n" \
            )

    comments += "Result image Width: " + str(wn) + "\n"
    comments += "Result image Height: " + str(hn) + "\n"

    img = [[0] * w for i in range(h)]

    print(im.height)
    print(im.width)
    print(im.mode)
    print(im.info)

    rgb_mode = False
    i_mode = 65536
    has_alpha = im.has_transparency_data
    if(not has_alpha):
        if(im.mode == "RGBA"):
            has_alpha = True
        elif (im.mode == "RGB"):
            rgb_mode = True
        else:
            s = im.mode.split(";")
            if(s[0] != "I"):
                exit("ERROR Exit! Unsupported image format " + im.mode)
            i_mode = 1 << int(s[1])

    comments += "Mode: " + str(im.mode) + "\n"
    comments += "Info: " + str(im.info) + "\n"

    print("Scale factor X: " + str(scale_factor_x) + "\n")
    print("Scale factor Y: " + str(scale_factor_y) + "\n")
 
    print("Result image Width: " + str(wn) + "\n")
    print("Result image Height: " + str(hn) + "\n")


    # scale_factor = 4

    result_array = []
    byte = 0
    byte_offset = 1
    for y in range(0, h, scale_factor_y):
        s = ""
        for x in range(0, w, scale_factor_x):

            vpx = [0] * (scale_factor_x * scale_factor_y)
            idx = 0
            
            for yy in range(scale_factor_y):
                for xx in range(scale_factor_x):
                    
                    if (has_alpha):
                        rgb = rgba2rgb(px[x + xx, y + yy])
                    elif rgb_mode:
                        rgb = px[x + xx, y + yy]
                    else:
                        pxx = scale_crop(px[x + xx, y + yy], i_mode//256)
                        rgb = [pxx, pxx, pxx]

                    vpx[idx] = get_y(color_invert(rgb))
                    
                    idx += 1
            
            r = sum(vpx) // (scale_factor_x * scale_factor_y)

            if(r > thr):
                img[y // scale_factor_y][x // scale_factor_x] = 1
            
            if(r > thr):
                s += "*"
            else: 
                s += " "

        print(s)
        comments += s + "\n"


    for n in range(hn2):
        for x in range(0, wn):
            for y in range(0, 8):
                yc = n * 8 + y
                if ((yc < hn) and (img[yc][x])):
                    byte = byte | byte_offset

                byte_offset = byte_offset << 1
                if(byte_offset >= 256):
                    result_array.append(byte)
                    byte = 0
                    byte_offset = 1
            
            if(byte_offset > 1):
                result_array.append(byte)
                byte = 0
                byte_offset = 1
        


    print(len(result_array))
    if(byte_offset > 1):
        result_array.append(byte)

    (hf, s_w, s_h, s_fl, s_d, s_fn) = save_to_h(filename, result_array, w=wn, h=hn, comments=comments, output_folder=output_folder)
    if(list_include != ""):
        f = open(os.path.join(output_folder, list_include), "at")
        f.write("#include \"" + hf + "\"\n")
        f.close()
    if(list_struct != ""):
        f = open(os.path.join(output_folder, list_struct), "at")
        f.write("{" + s_w + ", " + s_h + ", " + s_fl + ", " + s_d + ", " + s_fn + "},\n")
        f.close()
    
    print("Done!\n")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 2024.09.0001')
    parser.add_argument('--input', help='input filename', nargs=1, required=1)
    parser.add_argument('--append_include_list', help='filename for includes list (append)', nargs=1, default=[""])
    parser.add_argument('--append_struct_list', help='filename for struct list (append)', nargs=1, default=[""])
    parser.add_argument('--output_folder', help='output folder', nargs=1, default=["."])
    parser.add_argument('--dest_w', help='destination width', nargs=1, default=[16], type=int)
    parser.add_argument('--dest_h', help='destination height', nargs=1, default=[16], type=int)
    parser.add_argument('--thr', help='threshold', nargs=1, default=[127], type=int)
    args = parser.parse_args()
    print(args)
    print(args.input[0])
    print(args.dest_w[0], args.dest_h[0])

    sys.exit(main(args.input[0], list_include=args.append_include_list[0], list_struct=args.append_struct_list[0], output_folder=args.output_folder[0], \
                  dest_w=args.dest_w[0], dest_h=args.dest_h[0], thr=args.thr[0]))
    #print("Done!\n")
