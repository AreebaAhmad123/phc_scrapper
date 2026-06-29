import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
# Import the main processing function from your scraper script
from scrapper import parse_and_process

def scheduled_job():
    """
    Acts as the entry execution point when triggered by the tracker clock.
    """
    print("\n" + "="*50)
    print(f"Automated execution sequence started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    try:
        # Executes the unique row extraction and PDF downloading sequence
        parse_and_process()
    except Exception as e:
        print(f"Critical error encountered inside automated run: {e}")
    
    print(f"Scheduled run complete. Going back to standby loop...")
    print("="*50 + "\n")

def start_pipeline_scheduler():
    # BlockingScheduler keeps the script running continually as a dedicated background process
    scheduler = BlockingScheduler()
    
    print("Initializing automated production scraping engine...")
    
    # Production Configuration: Runs automatically every single day at 1:00 AM
    # scheduler.add_job(scheduled_job, 'cron', hour=1, minute=0)
    
    # Testing Configuration: Runs every 5 minutes so you can instantly verify it works
    scheduler.add_job(scheduled_job, 'interval', minutes=5)
    
    print("Job registered successfully. Background scheduler is active and monitoring time loops.")
    print("Leave this terminal open to maintain runtime. Press Ctrl+C to terminate safely.\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nShutdown signal received. Scheduler closed down safely.")

if __name__ == "__main__":
    start_pipeline_scheduler()