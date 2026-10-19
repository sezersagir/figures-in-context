"""Figures in Context from the command line.

    python -m figures_in_context app                       web app in the browser (recommended, everything in one place)

    python -m figures_in_context check-cases               check the test cases against the documents
    python -m figures_in_context new pilot [--test]        create a new run (--test: test models, no cost)
    python -m figures_in_context start <run>               stages 1–4: answers, check, judges, routing
    python -m figures_in_context review <run>              stage 5: just the review UI in the browser
    python -m figures_in_context report <run>              stage 6, after the review
    python -m figures_in_context calibration [--test]      do the judges find planted errors? (before the first real run)

Single stages: answers, check, judges, routing <run>.
<run> is the folder name under runs/ (e.g. 2026-10-20_pilot).
"""

import sys

from . import answers, check, judges, pipeline, report, review, routing


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    command, rest = argv[0], argv[1:]
    try:
        if command == "app":
            from . import app
            app.serve(port=int(rest[0]) if rest else 8765)
            return
        if command == "check-cases":
            count, problems = pipeline.check_cases()
            for p in problems:
                print(p)
            print(f"{count} test cases checked, {len(problems)} problems.")
            sys.exit(1 if problems else 0)
        if command == "calibration":
            from . import calibration
            run_dir = calibration.new(test="--test" in rest)
            ok = calibration.start(run_dir, calibration.load(run_dir.name)[1])
            if ok:
                print(f"Result: {run_dir / 'calibration.html'}")
            else:
                print(f"Continue with: python -m figures_in_context calibration-resume {run_dir.name}")
            return
        if command == "calibration-resume":
            from . import calibration
            run_dir, config = calibration.load(rest[0] if rest else "")
            calibration.start(run_dir, config)
            return
        if command == "new":
            if not rest:
                sys.exit("Name missing, e.g. `python -m figures_in_context new pilot`")
            run_dir = pipeline.new(rest[0], test="--test" in rest)
            print(f"Run created: {run_dir}")
            print(f"Continue with: python -m figures_in_context start {run_dir.name}")
            return
        if not rest:
            sys.exit(f"Run missing, e.g. `python -m figures_in_context {command} 2026-10-20_pilot`")
        run_dir, config, cases = pipeline.load_run(rest[0])
    except pipeline.RunError as e:
        sys.exit(str(e))

    if command == "start":
        pipeline.start(run_dir, config, cases)
    elif command == "answers":
        answers.run(run_dir, config, cases)
    elif command == "check":
        check.run(run_dir, cases)
    elif command == "judges":
        judges.run(run_dir, config, cases)
    elif command == "routing":
        routing.run(run_dir, config, cases)
    elif command == "review":
        review.serve(run_dir, cases)
    elif command == "report":
        report.run(run_dir, config, cases)
    else:
        sys.exit(f"Unknown command: {command}\n{__doc__}")


if __name__ == "__main__":
    main(sys.argv[1:])
