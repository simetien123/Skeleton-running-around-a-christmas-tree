import sys
import math
import os
import glob
import traceback

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from PIL import Image
except ImportError as e:
    print("Missing package:", e)
    print("\nRun:  pip install pygame PyOpenGL Pillow")
    input("\nPress Enter to exit...")
    sys.exit(1)

WIN_WIDTH, WIN_HEIGHT = 900, 700
NUM_SKELETONS = 5
ORBIT_RADIUS = 3.6
ORBIT_SPEED = 0.028
TREE_SPIN_SPEED = 0.4
ANIM_FPS = 12.0
SKELETON_SCALE = 1.65
TREE_SCALE = 2.8

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR = os.path.join(SCRIPT_DIR, "skeleton_clean")
TREE_PATH = os.path.join(SCRIPT_DIR, "tree.png")


def check_assets():
    if not os.path.isdir(FRAME_DIR):
        print("ERROR: Folder 'skeleton_clean' not found!")
        print(f"Expected: {FRAME_DIR}")
        input("Press Enter to exit...")
        sys.exit(1)

    frames = glob.glob(os.path.join(FRAME_DIR, "frame_*.png"))
    if len(frames) < 10:
        print("ERROR: Not enough frames in skeleton_clean/")
        input("Press Enter to exit...")
        sys.exit(1)

    if not os.path.isfile(TREE_PATH):
        print("ERROR: tree.png not found!")
        print(f"Expected: {TREE_PATH}")
        print("Put your Christmas tree image next to the script and name it tree.png")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"Found {len(frames)} skeleton frames + tree.png")


def make_window_transparent():
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll
        hwnd = pygame.display.get_wm_info()["window"]
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        LWA_COLORKEY = 0x00000001
        style = windll.user32.GetWindowLongA(hwnd, GWL_EXSTYLE)
        windll.user32.SetWindowLongA(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
        windll.user32.SetLayeredWindowAttributes(hwnd, 0x00000000, 0, LWA_COLORKEY)
        print("Transparent window enabled")
    except Exception as e:
        print("Could not enable transparency:", e)


def perspective(fovy, aspect, z_near, z_far):
    f = 1.0 / math.tan(math.radians(fovy) / 2.0)
    m = [0.0] * 16
    m[0] = f / aspect
    m[5] = f
    m[10] = (z_far + z_near) / (z_near - z_far)
    m[11] = -1.0
    m[14] = (2.0 * z_far * z_near) / (z_near - z_far)
    glMultMatrixf(m)


def look_at(eyex, eyey, eyez, cx, cy, cz, upx, upy, upz):
    fx, fy, fz = cx - eyex, cy - eyey, cz - eyez
    flen = math.sqrt(fx*fx + fy*fy + fz*fz) or 1.0
    fx, fy, fz = fx/flen, fy/flen, fz/flen
    sx = fy*upz - fz*upy
    sy = fz*upx - fx*upz
    sz = fx*upy - fy*upx
    slen = math.sqrt(sx*sx + sy*sy + sz*sz) or 1.0
    sx, sy, sz = sx/slen, sy/slen, sz/slen
    ux = sy*fz - sz*fy
    uy = sz*fx - sx*fz
    uz = sx*fy - sy*fx
    m = [sx, ux, -fx, 0.0, sy, uy, -fy, 0.0, sz, uz, -fz, 0.0, 0.0, 0.0, 0.0, 1.0]
    glMultMatrixf(m)
    glTranslatef(-eyex, -eyey, -eyez)


def load_texture(image):
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    data = image.tobytes("raw", "RGBA", 0, -1)
    w, h = image.size
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tex


def draw_textured_quad(w, h):
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-w, 0.0, 0.0)
    glTexCoord2f(1.0, 0.0); glVertex3f( w, 0.0, 0.0)
    glTexCoord2f(1.0, 1.0); glVertex3f( w, h, 0.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-w, h, 0.0)
    glEnd()


def draw_tree(tex_id, scale=TREE_SCALE):
    """Minecraft-style crossed planes (two quads at 90 degrees)."""
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor4f(1, 1, 1, 1)

    w = 0.7 * scale
    h = 1.6 * scale

    draw_textured_quad(w, h)

    glPushMatrix()
    glRotatef(90, 0, 1, 0)
    draw_textured_quad(w, h)
    glPopMatrix()

    glDisable(GL_TEXTURE_2D)


def draw_skeleton(tex_id, scale=SKELETON_SCALE):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor4f(1, 1, 1, 1)

    w = 0.95 * scale
    h = 1.70 * scale

    glPushMatrix()
    glScalef(-1.0, -1.0, 1.0)
    glTranslatef(0.0, -h, 0.0)

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-w, 0.0, 0.0)
    glTexCoord2f(1.0, 0.0); glVertex3f( w, 0.0, 0.0)
    glTexCoord2f(1.0, 1.0); glVertex3f( w, h, 0.0)
    glTexCoord2f(0.0, 1.0); glVertex3f(-w, h, 0.0)
    glEnd()

    glPopMatrix()
    glDisable(GL_TEXTURE_2D)


def main():
    check_assets()

    pygame.init()
    flags = DOUBLEBUF | OPENGL | NOFRAME
    pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT), flags)
    pygame.display.set_caption("Skeletons around Christmas Tree")

    make_window_transparent()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_ALPHA_TEST)
    glAlphaFunc(GL_GREATER, 0.1)
    glViewport(0, 0, WIN_WIDTH, WIN_HEIGHT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    perspective(45, WIN_WIDTH / float(WIN_HEIGHT), 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

    print("Loading textures...")
    paths = sorted(glob.glob(os.path.join(FRAME_DIR, "frame_*.png")))
    skeleton_textures = [load_texture(Image.open(p).convert("RGBA")) for p in paths]
    num_frames = len(skeleton_textures)

    tree_tex = load_texture(Image.open(TREE_PATH).convert("RGBA"))

    print(f"Loaded {num_frames} skeleton frames + tree.")
    print("Press ESC to quit.")

    clock = pygame.time.Clock()
    angle = 0.0
    tree_angle = 0.0
    anim_time = 0.0
    running = True

    while running:
        dt = clock.tick(30) / 1000.0
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False

        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glLoadIdentity()
        look_at(0, 3.2, 9.5, 0, 0.2, 0, 0, 1, 0)

        tree_angle += TREE_SPIN_SPEED * dt
        glPushMatrix()
        glTranslatef(0.0, -1.5, 0.0)
        glRotatef(math.degrees(tree_angle), 0, 1, 0)
        draw_tree(tree_tex)
        glPopMatrix()

        angle += ORBIT_SPEED
        anim_time += dt
        frame_idx = int(anim_time * ANIM_FPS) % num_frames

        for i in range(NUM_SKELETONS):
            a = angle + i * (2 * math.pi / NUM_SKELETONS)
            x = math.cos(a) * ORBIT_RADIUS
            z = math.sin(a) * ORBIT_RADIUS

            glPushMatrix()
            glTranslatef(x, -1.35, z)
            rot = -math.degrees(a) + 90
            glRotatef(rot, 0, 1, 0)
            bob = math.sin(anim_time * 13.0 + i) * 0.05
            glTranslatef(0, bob, 0)
            draw_skeleton(skeleton_textures[frame_idx])
            glPopMatrix()

        pygame.display.flip()

    for t in skeleton_textures:
        glDeleteTextures([t])
    glDeleteTextures([tree_tex])
    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n--- ERROR ---")
        traceback.print_exc()
        input("\nPress Enter to exit...")
