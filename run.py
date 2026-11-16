#!/usr/bin/env python3
"""Start PixelGlitch Studio."""
import sys

if __name__ == "__main__":
    if sys.argv[1:] == ["--smoke-test"]:
        from pixelglitch.smoke import main
        raise SystemExit(main())
    else:
        from pixelglitch.gui import main
        main()
