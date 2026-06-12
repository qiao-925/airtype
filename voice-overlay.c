#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"
#include <SDL2/SDL.h>
#include <math.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>

#define PILL_W  260
#define PILL_H   50
#define RADIUS   25
#define FONT_SZ  19

/* mode: argv[1]
 *   "listening"              — recording, show elapsed seconds
 *   "clipboard"              — copied to clipboard confirmation
 *   "error:<message>"        — error state with message
 */
enum mode_e { M_LISTENING, M_CLIPBOARD, M_ERROR };

static volatile sig_atomic_t running = 1;
static void on_signal(int s) { (void)s; running = 0; }

static int inside_round_rect(int x, int y, int w, int h, int r) {
    if (x < 0 || x >= w || y < 0 || y >= h) return 0;
    int r2 = r * r;
    if      (x < r && y < r)          return (r-x)*(r-x)+(r-y)*(r-y) <= r2;
    else if (x >= w-r && y < r)      return (x-(w-r-1))*(x-(w-r-1))+(r-y)*(r-y) <= r2;
    else if (x < r && y >= h-r)      return (r-x)*(r-x)+(y-(h-r-1))*(y-(h-r-1)) <= r2;
    else if (x >= w-r && y >= h-r)   return (x-(w-r-1))*(x-(w-r-1))+(y-(h-r-1))*(y-(h-r-1)) <= r2;
    return 1;
}

static SDL_Texture *make_pill(SDL_Renderer *r,
    Uint8 br, Uint8 bg, Uint8 bb, Uint8 ba,
    Uint8 bor, Uint8 bog, Uint8 bob, Uint8 boa)
{
    SDL_Surface *s = SDL_CreateRGBSurfaceWithFormat(0, PILL_W, PILL_H, 32,
                        SDL_PIXELFORMAT_ARGB8888);
    SDL_FillRect(s, NULL, SDL_MapRGBA(s->format,0,0,0,0));
    Uint32 fc = SDL_MapRGBA(s->format, br, bg, bb, ba);
    Uint32 bc = SDL_MapRGBA(s->format, bor, bog, bob, boa);

    for (int y = 0; y < PILL_H; y++)
        for (int x = 0; x < PILL_W; x++) {
            int outer = inside_round_rect(x, y, PILL_W, PILL_H, RADIUS);
            if (!outer) continue;
            int inner = inside_round_rect(x, y, PILL_W, PILL_H, RADIUS - 1);
            ((Uint32*)s->pixels)[y*(s->pitch>>2)+x] = inner ? fc : bc;
        }
    SDL_Texture *t = SDL_CreateTextureFromSurface(r, s);
    SDL_FreeSurface(s);
    return t;
}

static SDL_Texture *make_dot(SDL_Renderer *r, int size,
                              Uint8 cr, Uint8 cg, Uint8 cb, Uint8 ca)
{
    SDL_Surface *s = SDL_CreateRGBSurfaceWithFormat(0, size, size, 32,
                        SDL_PIXELFORMAT_ARGB8888);
    SDL_FillRect(s, NULL, SDL_MapRGBA(s->format,0,0,0,0));
    Uint32 c = SDL_MapRGBA(s->format, cr, cg, cb, ca);
    int cx = size/2, cy = size/2;
    int r2 = (size/2 - 1) * (size/2 - 1);
    for (int y = 0; y < size; y++)
        for (int x = 0; x < size; x++) {
            int dx = x - cx, dy = y - cy;
            if (dx*dx + dy*dy <= r2)
                ((Uint32*)s->pixels)[y*(s->pitch>>2)+x] = c;
        }
    SDL_Texture *t = SDL_CreateTextureFromSurface(r, s);
    SDL_FreeSurface(s);
    return t;
}

static unsigned char *load_file(const char *path, size_t *len) {
    int fd = open(path, O_RDONLY); if (fd < 0) return NULL;
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size <= 0) { close(fd); return NULL; }
    *len = st.st_size;
    unsigned char *d = mmap(NULL, *len, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    return d == MAP_FAILED ? NULL : d;
}

/* Decode one UTF-8 codepoint. Returns bytes consumed (1-4), or 0 on error. */
static int utf8_decode(const char *s, int *cp) {
    unsigned char c = (unsigned char)*s;
    if (c < 0x80) { *cp = c; return 1; }
    if ((c & 0xE0) == 0xC0) { *cp = c & 0x1F; return 2; }
    if ((c & 0xF0) == 0xE0) { *cp = c & 0x0F; return 3; }
    if ((c & 0xF8) == 0xF0) { *cp = c & 0x07; return 4; }
    *cp = 0xFFFD; return 1; /* replacement char */
}

static SDL_Texture *render_str(SDL_Renderer *ren, stbtt_fontinfo *font,
                               const char *str, SDL_Color c)
{
    float scl = stbtt_ScaleForPixelHeight(font, FONT_SZ);
    int asc, dsc, lg;
    stbtt_GetFontVMetrics(font, &asc, &dsc, &lg);
    int base = (int)(asc * scl);
    int h = (int)((asc - dsc + lg) * scl) + 6;

    /* First pass: measure width */
    float cx = 0;
    int prev_cp = 0;
    for (const char *p = str; *p; ) {
        int cp, adv, lsb;
        int n = utf8_decode(p, &cp);
        stbtt_GetCodepointHMetrics(font, cp, &adv, &lsb);
        if (p > str) cx += stbtt_GetCodepointKernAdvance(font, prev_cp, cp);
        cx += adv * scl;
        prev_cp = cp;
        p += n;
    }
    int w = (int)ceil(cx) + 4;

    SDL_Surface *sf = SDL_CreateRGBSurfaceWithFormat(0, w, h, 32, SDL_PIXELFORMAT_ARGB8888);
    SDL_FillRect(sf, NULL, SDL_MapRGBA(sf->format,0,0,0,0));

    /* Second pass: render glyphs */
    cx = 2;
    prev_cp = 0;
    for (const char *p = str; *p; ) {
        int cp;
        int n = utf8_decode(p, &cp);
        int cw, ch, xo, yo;
        unsigned char *bm = stbtt_GetCodepointBitmap(font, 0, scl, cp, &cw, &ch, &xo, &yo);
        if (bm) {
            for (int row = 0; row < ch; row++) {
                int dy = base + yo + row;
                int dx = (int)cx + xo;
                if (dy < 0 || dy >= h || dx < 0) continue;
                for (int col = 0; col < cw; col++) {
                    int px = dx + col;
                    if (px >= w) continue;
                    unsigned char a = bm[row * cw + col];
                    if (a) ((Uint32*)sf->pixels)[dy*(sf->pitch>>2)+px] =
                        SDL_MapRGBA(sf->format, c.r, c.g, c.b, (int)c.a * a / 255);
                }
            }
            stbtt_FreeBitmap(bm, font->userdata);
        }
        int adv, lsb;
        stbtt_GetCodepointHMetrics(font, cp, &adv, &lsb);
        if (p[n]) {
            int next_cp;
            utf8_decode(p + n, &next_cp);
            cx += stbtt_GetCodepointKernAdvance(font, cp, next_cp);
        }
        cx += adv * scl;
        prev_cp = cp;
        p += n;
    }
    SDL_Texture *t = SDL_CreateTextureFromSurface(ren, sf);
    SDL_FreeSurface(sf);
    return t;
}

/* Parse mode string. Returns mode enum, sets out_msg for error/clipboard. */
static enum mode_e parse_mode(const char *arg, const char **out_msg) {
    *out_msg = NULL;
    if (strncmp(arg, "error:", 6) == 0) {
        *out_msg = arg + 6;
        return M_ERROR;
    }
    if (strcmp(arg, "clipboard") == 0) return M_CLIPBOARD;
    return M_LISTENING;
}

/* Read elapsed seconds from /tmp/airtype-start-time. Returns 0 on failure. */
static int read_elapsed(void) {
    int fd = open("/tmp/airtype-start-time", O_RDONLY);
    if (fd < 0) return 0;
    char buf[32] = {0};
    int n = read(fd, buf, sizeof(buf)-1);
    close(fd);
    if (n <= 0) return 0;
    long start = atol(buf);
    if (start <= 0) return 0;
    time_t now = time(NULL);
    int elapsed = (int)(now - (time_t)start);
    return elapsed < 0 ? 0 : elapsed;
}

int main(int argc, char **argv) {
    const char *arg = (argc > 1) ? argv[1] : "listening";
    const char *err_msg = NULL;
    enum mode_e mode = parse_mode(arg, &err_msg);

    /* Color palette */
    Uint8 br = 38, bg_p = 38, bb_p = 46, ba_p = 235;
    Uint8 bor = 255, bog = 255, bob = 255, boa = 6;

    /* Dot/text colors per mode */
    Uint8 dr, dg, db;
    SDL_Color txt_clr = {0xf0, 0xf0, 0xf4, 255};
    switch (mode) {
    case M_LISTENING:
        dr = 0x64; dg = 0xD2; db = 0xFF;   /* cyan */
        break;
    case M_CLIPBOARD:
        dr = 0x64; dg = 0xFF; db = 0x64;   /* green */
        break;
    case M_ERROR:
        dr = 0xFF; dg = 0x55; db = 0x55;   /* red */
        break;
    }

    signal(SIGTERM, on_signal); signal(SIGINT, on_signal);

    if (SDL_Init(SDL_INIT_VIDEO) < 0) { SDL_ClearError(); SDL_Init(SDL_INIT_VIDEO); }

    const char *paths[] = {
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf", NULL};
    size_t flen = 0; unsigned char *fdata = NULL;
    for (int i = 0; paths[i]; i++) { fdata = load_file(paths[i], &flen); if (fdata) break; }
    if (!fdata) return 1;
    stbtt_fontinfo font;
    if (!stbtt_InitFont(&font, fdata, 0)) return 1;

    SDL_Window *win = SDL_CreateWindow("",
        SDL_WINDOWPOS_CENTERED_DISPLAY(0), SDL_WINDOWPOS_CENTERED_DISPLAY(0),
        PILL_W, PILL_H,
        SDL_WINDOW_BORDERLESS | SDL_WINDOW_ALWAYS_ON_TOP | SDL_WINDOW_SKIP_TASKBAR);
    if (!win) return 1;
    SDL_SetWindowBordered(win, SDL_FALSE);

    SDL_Renderer *ren = SDL_CreateRenderer(win, -1,
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!ren) ren = SDL_CreateRenderer(win, -1, SDL_RENDERER_SOFTWARE | SDL_RENDERER_PRESENTVSYNC);
    if (!ren) return 1;

    SDL_Texture *bg = make_pill(ren, br, bg_p, bb_p, ba_p, bor, bog, bob, boa);
    if (!bg) return 1;

    /* Initial text: listening shows "0s", others use mode label */
    char label_buf[64];
    const char *label_str;
    if (mode == M_LISTENING) {
        snprintf(label_buf, sizeof(label_buf), "0s");
        label_str = label_buf;
    } else if (mode == M_ERROR && err_msg) {
        label_str = err_msg;
    } else if (mode == M_CLIPBOARD) {
        label_str = "copied!";
    }
    SDL_Texture *txt = render_str(ren, &font, label_str, txt_clr);
    SDL_Texture *d_hi = make_dot(ren, 14, dr, dg, db, 255);
    SDL_Texture *d_lo = make_dot(ren, 14, dr, dg, db, 56);
    if (!txt || !d_hi || !d_lo) return 1;

    int tw, th, dw, dh;
    SDL_QueryTexture(txt, NULL, NULL, &tw, &th);
    SDL_QueryTexture(d_hi, NULL, NULL, &dw, &dh);

    Uint64 tick = SDL_GetTicks64();
    Uint64 text_tick = SDL_GetTicks64();  /* for text refresh in listening */
    int dot_on = 1;
    int last_elapsed = -1;

    /* Animation intervals (ms) */
    Uint64 dot_interval = (mode == M_LISTENING) ? 1000 : 600;
    Uint64 text_interval = (mode == M_LISTENING) ? 1000 : 0;  /* 0 = no refresh */

    while (running) {
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) { if (ev.type == SDL_QUIT) running = 0; }

        Uint64 now = SDL_GetTicks64();

        /* Dot blink */
        if (now - tick >= dot_interval) {
            tick = now; dot_on = !dot_on;
        }

        /* Text refresh: listening mode reads elapsed seconds */
        if (text_interval > 0 && now - text_tick >= text_interval) {
            text_tick = now;
            int el = read_elapsed();
            if (el != last_elapsed) {
                last_elapsed = el;
                if (txt) SDL_DestroyTexture(txt);
                snprintf(label_buf, sizeof(label_buf), "%ds", el);
                txt = render_str(ren, &font, label_buf, txt_clr);
                if (txt) SDL_QueryTexture(txt, NULL, NULL, &tw, &th);
            }
        }

        int ww, wh; SDL_GetWindowSize(win, &ww, &wh);
        int gap = 10;
        int total_w = dw + gap + tw, total_h = dw > th ? dw : th;
        int sx = (ww - total_w) / 2, sy = (wh - total_h) / 2;

        SDL_SetRenderDrawColor(ren, 0,0,0,0);
        SDL_RenderClear(ren);

        SDL_Rect pr = {0,0,ww,wh}; SDL_RenderCopy(ren, bg, NULL, &pr);
        SDL_Rect dr_r = {sx, sy+(total_h-dw)/2, dw, dh};
        SDL_RenderCopy(ren, dot_on?d_hi:d_lo, NULL, &dr_r);
        SDL_Rect tr = {sx+dw+gap, sy+(total_h-th)/2 + 2, tw, th};
        SDL_RenderCopy(ren, txt, NULL, &tr);

        SDL_RenderPresent(ren);
    }

    SDL_DestroyTexture(bg); SDL_DestroyTexture(txt);
    SDL_DestroyTexture(d_hi); SDL_DestroyTexture(d_lo);
    SDL_DestroyRenderer(ren); SDL_DestroyWindow(win);
    munmap(fdata, flen); SDL_Quit();
    return 0;
}
