import sys
import logging
import os
from waltz.command_line import parse_command_line
from waltz.exceptions import (WaltzException, WaltzServiceNotFound, 
                             WaltzAmbiguousResource, WaltzResourceNotFound)


def setup_logging(args=None):
    """Set up logging configuration with optional file output."""
    # Create logs directory if it doesn't exist
    log_level = logging.INFO
    
    # Check if we have a waltz directory and logging is desired
    waltz_dir = getattr(args, 'waltz_directory', './') if args else './'
    log_dir = os.path.join(waltz_dir, 'logs') if waltz_dir else './logs'
    
    # Basic logging setup - always to console at WARNING level or higher
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    
    # Try to add file logging if possible
    try:
        if waltz_dir and os.path.exists(waltz_dir):
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'waltz.log')
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            logging.getLogger().addHandler(file_handler)
            logging.getLogger().setLevel(logging.INFO)
    except (OSError, PermissionError):
        # If we can't create log files, just continue without file logging
        pass


def print_friendly_error(error, show_help_hint=True):
    """Print a user-friendly error message."""
    print(f"❌ Error: {error}", file=sys.stderr)
    
    if show_help_hint:
        print("💡 Try 'waltz --help' or 'waltz <command> --help' for usage information.", file=sys.stderr)
    
    # Log the full error for debugging
    logging.info(f"Full error details: {error}", exc_info=True)


def suggest_next_steps(error):
    """Provide helpful suggestions based on the error type."""
    if isinstance(error, WaltzServiceNotFound):
        print("💡 Available commands:", file=sys.stderr)
        print("   • Run 'waltz list' to see available services", file=sys.stderr)
        print("   • Use 'waltz configure <service-type> <name>' to add a new service", file=sys.stderr)
        print("   • Example: waltz configure canvas my_canvas --base https://canvas.example.com/ --course 12345 --token your_token", file=sys.stderr)
    elif isinstance(error, WaltzResourceNotFound):
        print("💡 Available commands:", file=sys.stderr)
        print("   • Run 'waltz list <service>' to see available resources", file=sys.stderr)
        print("   • Check the spelling of the resource name", file=sys.stderr)
        print("   • Use 'waltz search <category> <term>' to find resources", file=sys.stderr)
    elif "Service canvas is not configured" in str(error):
        print("💡 To use Canvas, you need to configure it first:", file=sys.stderr)
        print("   waltz configure canvas <name> --base <canvas_url> --course <course_id> --token <api_token>", file=sys.stderr)
        print("   Get your API token from Canvas → Account → Settings → New Access Token", file=sys.stderr)
    elif "No registry file was detected" in str(error) or "NoneType" in str(error):
        print("💡 It looks like Waltz isn't initialized in this directory:", file=sys.stderr)
        print("   • Run 'waltz init' to set up Waltz here", file=sys.stderr)
        print("   • Or navigate to a directory where Waltz is already set up", file=sys.stderr)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    
    try:
        # Parse args first to potentially get waltz_directory for logging
        if args and '--waltz_directory' in args:
            idx = args.index('--waltz_directory')
            if idx + 1 < len(args):
                waltz_dir = args[idx + 1]
                setup_logging(type('Args', (), {'waltz_directory': waltz_dir})())
        else:
            setup_logging()
        
        logging.info(f"Starting Waltz with args: {args}")
        result = parse_command_line(args)
        logging.info("Waltz command completed successfully")
        return result
        
    except WaltzServiceNotFound as e:
        print_friendly_error(f"Unknown or unconfigured service: {e}")
        suggest_next_steps(e)
        sys.exit(1)
        
    except WaltzResourceNotFound as e:
        print_friendly_error(f"Could not find the requested resource: {e}")
        suggest_next_steps(e)
        sys.exit(1)
        
    except WaltzAmbiguousResource as e:
        print_friendly_error(f"Multiple resources match your request: {e}")
        print("💡 Try being more specific with your resource name or use --id to specify exactly which resource you want.", file=sys.stderr)
        sys.exit(1)
        
    except WaltzException as e:
        print_friendly_error(str(e))
        suggest_next_steps(e)
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user.", file=sys.stderr)
        logging.info("Operation cancelled by user (KeyboardInterrupt)")
        sys.exit(130)
        
    except Exception as e:
        # For unexpected errors, provide a helpful message but still show some details
        print("❌ An unexpected error occurred:", file=sys.stderr)
        print(f"   {type(e).__name__}: {e}", file=sys.stderr)
        print("💡 This might be a bug. Consider reporting it if the problem persists.", file=sys.stderr)
        print("💡 Check the log file (logs/waltz.log) for more details if available.", file=sys.stderr)
        
        # Log the full traceback for debugging
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
