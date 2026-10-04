import argparse
import time

from tts_player import AssistantSpeechPlayer


def main() -> None:
    parser = argparse.ArgumentParser(description='Live Edge TTS playback test using game voice settings')
    parser.add_argument(
        '--text',
        default='This is a live voice test with the same assistant voice settings as the game.',
        help='Text to synthesize and play',
    )
    args = parser.parse_args()

    player = AssistantSpeechPlayer(delay_seconds=0)
    try:
        print('Playing live TTS now...')
        player.speak_async(args.text)
        # Wait for worker thread to process one queued utterance.
        time.sleep(6)
    finally:
        player.stop()


if __name__ == '__main__':
    main()
