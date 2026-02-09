#!/bin/bash
# Demo script for Meta-Factory
# Usage: ./run_demo.sh [greenfield|brownfield|greyfield] [provider]

set -e

cd "$(dirname "$0")/.."

# Check if venv is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

MODE="${1:-greenfield}"
PROVIDER="${2:-}"

echo "============================================"
echo "  Meta-Factory Demo"
echo "============================================"
echo ""

# List available providers
echo "Checking available providers..."
python main.py --list-providers
echo ""

case $MODE in
    greenfield)
        echo "Running GREENFIELD demo..."
        echo "Input: Discovery call transcript"
        echo ""

        if [[ -n "$PROVIDER" ]]; then
            python main.py \
                --input demo/greenfield/discovery_call_transcript.txt \
                --client "TechFlow Industries" \
                --mode greenfield \
                --provider "$PROVIDER" \
                --max-cost 3.00
        else
            python main.py \
                --input demo/greenfield/discovery_call_transcript.txt \
                --client "TechFlow Industries" \
                --mode greenfield \
                --max-cost 3.00
        fi
        ;;

    brownfield)
        echo "Running BROWNFIELD demo..."
        echo "Input: Legacy system description"
        echo ""

        if [[ -n "$PROVIDER" ]]; then
            python main.py \
                --input demo/brownfield/legacy_system_description.txt \
                --client "TechFlow Industries" \
                --mode brownfield \
                --provider "$PROVIDER" \
                --max-cost 3.00
        else
            python main.py \
                --input demo/brownfield/legacy_system_description.txt \
                --client "TechFlow Industries" \
                --mode brownfield \
                --max-cost 3.00
        fi
        ;;

    greyfield)
        echo "Running GREYFIELD demo..."
        echo "Input: New requirements + existing system"
        echo ""

        if [[ -n "$PROVIDER" ]]; then
            python main.py \
                --input demo/greyfield/new_requirements.txt \
                --codebase demo/greyfield/existing_system.txt \
                --client "TechFlow Industries" \
                --mode greyfield \
                --provider "$PROVIDER" \
                --max-cost 5.00
        else
            python main.py \
                --input demo/greyfield/new_requirements.txt \
                --codebase demo/greyfield/existing_system.txt \
                --client "TechFlow Industries" \
                --mode greyfield \
                --max-cost 5.00
        fi
        ;;

    classify)
        echo "Running classification only..."
        python main.py \
            --input demo/greenfield/discovery_call_transcript.txt \
            --client "Test" \
            --classify-only
        ;;

    *)
        echo "Usage: $0 [greenfield|brownfield|greyfield|classify] [provider]"
        echo ""
        echo "Modes:"
        echo "  greenfield  - New project from discovery transcript"
        echo "  brownfield  - Legacy system modernization"
        echo "  greyfield   - Existing system + new requirements"
        echo "  classify    - Just classify input (no API calls)"
        echo ""
        echo "Providers:"
        echo "  anthropic   - Claude (default)"
        echo "  openai      - GPT-4"
        echo "  gemini      - Google Gemini"
        echo "  deepseek    - Deepseek"
        echo ""
        echo "Examples:"
        echo "  $0 greenfield"
        echo "  $0 brownfield openai"
        echo "  $0 greyfield gemini"
        exit 1
        ;;
esac

echo ""
echo "Demo complete! Check ./outputs for results."
