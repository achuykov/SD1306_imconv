# SD1306_imconv
Converts input image (RGB/RGBA) to SD1306 format

## Usage
Just type in command line
```
imconv.py --input image.png --output_folder res --append_include_list inc_imgs.h --append_struct_list inc_struct.h
```

Or in `for` loop, for example for Windows Batch file
```
@echo off
SET count=1
del /q /f res\inc_imgs.h
del /q /f res\inc_struct.h
FOR %%G IN ("C:\Images\*.png") DO (
 echo %count%:%%G
 imconv.py --input %%G --output_folder res --append_include_list inc_imgs.h --append_struct_list inc_struct.h
 set /a count+=1 )

```

And later, in C code in global space 
```C
    #include "inc_imgs.h"
    
    const ImageData images[] = {
        #include "inc_struct.h"
    };
```

And in function
```C
    const size_t images_count = sizeof(images) / sizeof(images[0]);
    size_t idx = 0;
    while(1)
    {
        ssd1306_draw_image(0, 32, images[idx].w, images[idx].h, images[idx].data);
        Delay_Ms(SLIDE_SHOW_DELAY);
        idx = (idx + 1) % images_count;
    }
```