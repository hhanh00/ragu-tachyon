#!/usr/bin/env zsh
# Regenerate a chapter's narration, slide video, subtitles and final video.
#
# Usage: audio/make_video.sh [--skip-audio] STEM [STEM ...]
#
# STEM is a script name without .txt, such as 03-statements-and-challenges.
# The deck is audio/slides/deck_NN.py, where NN is the stem's first two digits.
# Environment: VOICE and SPEED (passed to render.py), KOKORO (model directory,
# default .kokoro), WORK (slide clip cache, default /tmp/slides-work).
# See audio/README.md for the one-time setup.
set -e

ROOT=${0:A:h:h}
AUDIO=$ROOT/audio
WORK=${WORK:-/tmp/slides-work}
KOKORO=${KOKORO:-$ROOT/.kokoro}
SKIP_AUDIO=0
if [[ $1 == --skip-audio ]]; then SKIP_AUDIO=1; shift; fi
(( $# )) || { sed -n '2,10p' $0; exit 1; }

for STEM in "$@"; do
  NN=${STEM[1,2]}
  [[ -f $AUDIO/scripts/$STEM.txt ]] || { echo "no script audio/scripts/$STEM.txt"; exit 1; }
  [[ -f $AUDIO/slides/deck_$NN.py ]] || { echo "no deck audio/slides/deck_$NN.py"; exit 1; }
  echo "== $STEM"

  if (( ! SKIP_AUDIO )); then
    (cd $AUDIO && $ROOT/.tts-venv/bin/python render.py $KOKORO scripts out --force --only $STEM | tail -1)
  fi
  (cd $AUDIO/slides && $ROOT/.manim-venv/bin/python build.py deck_$NN video --work $WORK | tail -1)
  (cd $AUDIO && $ROOT/.manim-venv/bin/python slides/subtitles.py $STEM | tail -1)

  OUT=$AUDIO/out
  ffmpeg -y -loglevel error \
    -i $OUT/$STEM-slides.mp4 -i $OUT/$STEM.m4a -i $OUT/$STEM-slides.srt \
    -map 0:v -map 1:a -map 2 -c:v copy -c:a copy -c:s mov_text \
    -metadata:s:s:0 language=eng -shortest $OUT/$STEM-video.mp4
  echo "wrote audio/out/$STEM-video.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 $OUT/$STEM-video.mp4 | cut -d. -f1) s)"
done
