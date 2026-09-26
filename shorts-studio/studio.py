#!/usr/bin/env python3
"""Shorts Studio: episode JSON -> Google Flow (Omni) prompts -> ready-to-upload vertical Short.

  python studio.py refs    episodes/ep001_tomaten.json
  python studio.py prompts episodes/ep001_tomaten.json --lang de
  python studio.py build   episodes/ep001_tomaten.json --lang de [--align whisper] [--music music/bg.mp3]

Clips are read from clips/<episode id>/<lang>/<shot id>.mp4 (e.g. clips/ep001/de/01.mp4).
Output goes to out/<episode id>/.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
CLIP_MIN, CLIP_MAX = 3, 10  # Omni Flash clip length range (seconds)
WORDS_PER_SEC = 2.4         # relaxed cartoon speaking pace

LANG_NAME = {"de": "German", "en": "English"}

CONFIG = {
    "font": "Arial Black",          # any installed font, or a .ttf dropped into fonts/
    "font_size": 104,
    "caption_y": 1300,              # vertical centre of the captions (of 1920)
    "highlight": "&H0033D6FF",      # ASS BGR colour for *emphasised* words (yellow)
    "watermark": "@BlütenGeheimnis",
    "music_volume": 0.10,
    "loudness": -14,
}


# ---------------------------------------------------------------- helpers

def ffmpeg_bin():
    exe = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found: install ffmpeg or `pip install imageio-ffmpeg`.")


def run(args, capture=False):
    res = subprocess.run(args, stdout=subprocess.PIPE if capture else None,
                         stderr=subprocess.PIPE, text=True)
    if res.returncode != 0 and not capture:
        sys.exit("ffmpeg failed:\n" + res.stderr[-3000:])
    return res.stderr


def probe(path):
    """Duration and audio presence, parsed from `ffmpeg -i` (no ffprobe needed)."""
    info = run([ffmpeg_bin(), "-hide_banner", "-i", path], capture=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    if not m:
        sys.exit(f"Cannot read clip: {path}")
    dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    return dur, "Audio:" in info


def speech_intervals(path, start, end):
    """Non-silent stretches of the clip between start and end (clip-relative seconds)."""
    info = run([ffmpeg_bin(), "-hide_banner", "-ss", str(start), "-to", str(end), "-i", path,
                "-af", "silencedetect=n=-32dB:d=0.25", "-f", "null", "-"], capture=True)
    length = end - start
    silences, cur = [], None
    for line in info.splitlines():
        if "silence_start" in line:
            cur = max(0.0, float(line.split("silence_start:")[1].split()[0]))
        elif "silence_end" in line and cur is not None:
            silences.append((cur, float(line.split("silence_end:")[1].split()[0])))
            cur = None
    if cur is not None:
        silences.append((cur, length))
    spans, t = [], 0.0
    for s, e in silences:
        if s - t > 0.15:
            spans.append((t, s))
        t = max(t, e)
    if length - t > 0.15:
        spans.append((t, length))
    return spans or [(0.0, length)]


def tokens(line):
    """Split a script line into (word, emphasised) pairs; *word* marks emphasis."""
    out, emph = [], False
    for raw in line.split():
        starts, ends = raw.startswith("*"), raw.rstrip(".,!?;:…").endswith("*")
        if starts:
            emph = True
        word = raw.replace("*", "")
        if word:
            out.append((word, emph))
        if ends:
            emph = False
    return out


def estimate_timings(words, spans):
    """Spread words over the voiced spans, weighted by length plus a pause after punctuation."""
    weights = [len(w) + 2 + (4 if w[-1] in ".,!?;:…" else 0) for w, _ in words]
    total_w = sum(weights)
    total_t = sum(e - s for s, e in spans)

    def to_clip_time(x):  # x: seconds along the concatenated voiced spans
        for s, e in spans:
            if x <= e - s:
                return s + x
            x -= e - s
        return spans[-1][1]

    acc, out = 0.0, []
    for (w, emph), wt in zip(words, weights):
        out.append((to_clip_time(acc / total_w * total_t), w, emph))
        acc += wt
    return out


def whisper_timings(path, start, end, lang, script_words):
    from faster_whisper import WhisperModel
    global _WHISPER
    if "_WHISPER" not in globals():
        _WHISPER = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = _WHISPER.transcribe(path, language=lang, word_timestamps=True,
                                  clip_timestamps=[start, end])
    heard = [(w.start - start, w.word.strip()) for s in segs for w in s.words if w.word.strip()]
    if len(heard) == len(script_words):  # same word count: keep script spelling + emphasis
        return [(t, w, e) for (t, _), (w, e) in zip(heard, script_words)]
    return [(t, w, False) for t, w in heard]


def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# ---------------------------------------------------------------- commands

def load(path):
    with open(path, encoding="utf-8") as f:
        ep = json.load(f)
    with open(os.path.join(ROOT, "characters.json"), encoding="utf-8") as f:
        base = json.load(f)
    cast = dict(base["characters"], **ep.get("cast", {}))
    return ep, base, cast


def clip_seconds(n_words):
    """Shortest Omni clip that fits the line with a little breathing room (shorter = fewer credits)."""
    return max(CLIP_MIN, min(CLIP_MAX, math.ceil(n_words / WORDS_PER_SEC + 1.2)))


def cmd_refs(args):
    """Image prompts for the reference sheets attached to every Omni shot."""
    ep, base, cast = load(args.episode)
    names = sorted({c for shot in ep["shots"] for c in shot["chars"]})
    blocks = [f"=== REFERENCE: {cast[c]['name']}  (save as refs/{c}.png, reuse in every episode)\n"
              f"{base['style']}\nFull-body character reference sheet on a plain light background, "
              f"front view, neutral friendly expression: {cast[c]['look']}\n{base['negative']}\n"
              for c in names]
    text = "\n".join(blocks)
    out = os.path.join(ROOT, "out", ep["id"], "reference_prompts.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"-> {out}")


def cmd_prompts(args):
    ep, base, cast = load(args.episode)
    lang = args.lang
    blocks = []
    for shot in ep["shots"]:
        n_words = len(tokens(shot["line"][lang]))
        secs = clip_seconds(n_words)
        too_long = n_words / WORDS_PER_SEC + 1.2 > CLIP_MAX
        who = cast[shot["speaker"]]
        chars = "\n".join(f"- {cast[c]['name']}: {cast[c]['look']}" for c in shot["chars"])
        line = shot["line"][lang].replace("*", "")
        blocks.append(
            f"=== SHOT {shot['id']}  (save as clips/{ep['id']}/{lang}/{shot['id']}.mp4)\n"
            f"Omni settings: 9:16, {secs} s, 360p (upscale the keeper to 720p for free) | "
            f"references: {', '.join('refs/' + c + '.png' for c in shot['chars'])}"
            + (f"\n!! {n_words} words: probably too long for {CLIP_MAX} s, split this shot" if too_long else "")
            + f"\nSTYLE: {base['style']}\nCHARACTERS:\n{chars}\nSCENE: {shot['scene']}\n"
            f"DIALOGUE: {who['name']} says in {LANG_NAME[lang]} ({who['voice'][lang]}): \"{line}\"\n"
            f"Only {who['name']} speaks; lips move only while speaking. Light ambient garden sounds.\n"
            f"{base['negative']}\n")
    text = "\n".join(blocks)
    out = os.path.join(ROOT, "out", ep["id"], f"flow_prompts_{lang}.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"-> {out}")


def cmd_build(args):
    ep, _, _ = load(args.episode)
    lang, cfg = args.lang, CONFIG
    clip_dir = os.path.join(ROOT, "clips", ep["id"], lang)
    out_dir = os.path.join(ROOT, "out", ep["id"])
    os.makedirs(out_dir, exist_ok=True)

    inputs, vf, af, events, srt = [], [], [], [], []
    offset = 0.0
    for i, shot in enumerate(ep["shots"]):
        path = os.path.join(clip_dir, f"{shot['id']}.mp4")
        if not os.path.exists(path):
            sys.exit(f"Missing clip: {path}")
        dur, has_audio = probe(path)
        start, end = shot.get("trim", [0, dur])
        end = min(end, dur)
        length = end - start
        inputs += ["-ss", str(start), "-t", str(length), "-i", path]

        if args.fit == "blur":
            vf.append(f"[{i}:v]split[a{i}][b{i}];"
                      f"[a{i}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30[bg{i}];"
                      f"[b{i}]scale={W}:{H}:force_original_aspect_ratio=decrease[fg{i}];"
                      f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,fps={FPS},setsar=1,format=yuv420p[v{i}]")
        else:
            vf.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
                      f"fps={FPS},setsar=1,format=yuv420p[v{i}]")
        if has_audio:
            af.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
                      f"apad,atrim=0:{length:.3f}[a{i}]")
        else:
            af.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{length:.3f}[a{i}]")

        words = tokens(shot["line"][lang])
        if args.align == "whisper" and has_audio:
            timed = whisper_timings(path, start, end, lang, words)
        else:
            spans = speech_intervals(path, start, end) if has_audio else [(0.0, length)]
            timed = estimate_timings(words, spans)
        for j, (t, w, emph) in enumerate(timed):
            t_end = timed[j + 1][0] if j + 1 < len(timed) else min(length, t + 0.8)
            t_end = max(t_end, t + 0.15)
            colour = f"\\c{cfg['highlight']}" if emph else ""
            events.append((offset + t, offset + t_end,
                           "{\\fscx70\\fscy70\\t(0,90,\\fscx108\\fscy108)\\t(90,160,\\fscx100\\fscy100)"
                           + colour + "}" + w.upper().replace("{", "(").replace("}", ")")))
        if timed:
            srt.append((offset + timed[0][0], offset + min(length, timed[-1][0] + 0.8),
                        shot["line"][lang].replace("*", "")))
        offset += length

    ass_path = os.path.join(out_dir, f"{ep['id']}_{lang}.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\n\n" % (W, H))
        f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, "
                "Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write(f"Style: Cap,{cfg['font']},{cfg['font_size']},&H00FFFFFF,&H00FFFFFF,&H00000000,"
                "&H64000000,1,0,0,0,100,100,1,0,1,9,4,5,40,40,0,1\n")
        f.write(f"Style: Mark,{cfg['font']},38,&H99FFFFFF,&H99FFFFFF,&HAA000000,&H00000000,"
                "1,0,0,0,100,100,0,0,1,2,0,9,0,40,70,1\n\n")
        f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        if cfg["watermark"]:
            f.write(f"Dialogue: 0,{ass_time(0)},{ass_time(offset)},Mark,,0,0,0,,{cfg['watermark']}\n")
        for s, e, text in events:
            f.write(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,"
                    f"{{\\pos({W // 2},{cfg['caption_y']})}}{text}\n")

    with open(os.path.join(out_dir, f"{ep['id']}_{lang}.srt"), "w", encoding="utf-8") as f:
        for k, (s, e, text) in enumerate(srt, 1):
            f.write(f"{k}\n{srt_time(s)} --> {srt_time(e)}\n{text}\n\n")

    n = len(ep["shots"])
    concat = "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]"
    esc = lambda p: p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    subs = f"[cv]subtitles='{esc(ass_path)}':fontsdir='{esc(os.path.join(ROOT, 'fonts'))}'[vout]"
    audio = f"[ca]loudnorm=I={cfg['loudness']}:TP=-1.5:LRA=11[aout]"
    if args.music:
        inputs += ["-stream_loop", "-1", "-i", args.music]
        audio = (f"[{n}:a]volume={cfg['music_volume']},atrim=0:{offset:.3f}[bgm];"
                 f"[ca][bgm]amix=inputs=2:duration=first:normalize=0,"
                 f"loudnorm=I={cfg['loudness']}:TP=-1.5:LRA=11[aout]")
    graph = ";".join(vf + af + [concat, subs, audio])

    video = os.path.join(out_dir, f"{ep['id']}_{lang}.mp4")
    run([ffmpeg_bin(), "-hide_banner", "-y", *inputs, "-filter_complex", graph,
         "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", video])

    meta = ep["meta"][lang]
    with open(os.path.join(out_dir, f"{ep['id']}_{lang}_upload.txt"), "w", encoding="utf-8") as f:
        f.write(f"TITLE:\n{meta['title']}\n\nDESCRIPTION:\n{meta['description']}\n\n"
                f"{' '.join(meta['hashtags'])}\n")
    print(f"-> {video}  ({offset:.1f} s)")
    if offset > 60:
        print("!! Longer than 60 s: trim shots (\"trim\": [start, end]) to stay Shorts-friendly.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("refs", help="write image prompts for the character reference sheets")
    pp = sub.add_parser("prompts", help="write Google Flow (Omni) prompts for every shot")
    pb = sub.add_parser("build", help="assemble clips into a captioned vertical Short")
    for sp in (pr, pp, pb):
        sp.add_argument("episode")
    for sp in (pp, pb):
        sp.add_argument("--lang", choices=sorted(LANG_NAME), default="de")
    pb.add_argument("--align", choices=["auto", "whisper"], default="auto",
                    help="caption timing: silence-based estimate, or faster-whisper word timestamps")
    pb.add_argument("--fit", choices=["crop", "blur"], default="crop",
                    help="how to fit non-vertical clips into 9:16")
    pb.add_argument("--music", help="optional background music file (mixed quietly, looped)")
    args = p.parse_args()
    {"refs": cmd_refs, "prompts": cmd_prompts, "build": cmd_build}[args.cmd](args)


if __name__ == "__main__":
    main()
