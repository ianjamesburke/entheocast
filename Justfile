set dotenv-load

# rebuild index.html from template + current data
build:
    cd pipeline && uv run python build.py

# run full pipeline (fetch + build), optional: just run --since 2026-01-01
run *args:
    cd pipeline && uv run python run.py {{args}}

# build + commit + push (message required: just release "fix: ...")
release msg: build
    git add index.html
    git diff --cached --quiet || git commit -m "{{msg}}"
    git push

# commit everything staged + push
push msg:
    git diff --cached --quiet || git commit -m "{{msg}}"
    git push

# install pipeline deps
install:
    cd pipeline && uv sync
