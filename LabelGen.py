from PIL import Image, ImageFont, ImageDraw
import qrcode
import textwrap


class CustomLabel:
    def __init__(self, text=None, content=None):
        self.dimensions = (600, 360)
        self.default_path = "label.png"
        self.font = ImageFont.truetype("Resources/Arial Bold.ttf", 30)
        self.qr_code_border = 15
        self.chars_per_line = 14

        # content of the QR code
        self.content = content
        # text displayed on label
        self.text = text

    def qr_code(self, content, size=360):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=0,
        )
        qr.add_data(self.content)
        qr.make(fit=True)

        # make_image() creates the Pillow Image object
        img = qr.make_image(fill_color="black", back_color="white")

        img.save('temp_qr_code.png')
        pil_image = Image.open('temp_qr_code.png')
        pil_image = pil_image.resize((size, size))

        return pil_image

    def canvas(self):
        img = Image.new("RGB", self.dimensions, (255, 255, 255))
        return img

    def compile_image(self):
        canvas = self.canvas()

        qr_code_img = self.qr_code(self.content, size=self.dimensions[1]-2*self.qr_code_border)
        canvas.paste(qr_code_img, (self.qr_code_border, self.qr_code_border))

        right_center = (self.dimensions[0]+self.dimensions[1]-self.qr_code_border)/2
        self.write_text(canvas, self.text, pos=(right_center, self.dimensions[1]*0.5))

        return canvas

    def write_text(self, canvas, text, pos=(0, 0)):
        def create_image(size, message, font, fontColor):
            W, H = size
            draw = ImageDraw.Draw(canvas)
            _, _, w, h = draw.textbbox((0, 0), message, font=font)
            draw.text((W - w/2, H - h/2), message, font=font, fill=fontColor)
            return canvas

        create_image(pos, textwrap.fill(text, self.chars_per_line), self.font, (0, 0, 0))

    def save(self, path=None):
        if path is None:
            path = self.default_path
        img = self.compile_image()
        img.save(path)
        return path

if __name__ == '__main__':
    label = CustomLabel("01NA012345")
    label.save()
