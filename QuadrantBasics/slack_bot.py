import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from main import create_qdrant_database, retrieve_docs, question_pdf, retrieve_doc_by_metadata

# Load environment variables from .env file
load_dotenv()

# Initialize the Slack app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Store company associations for channels
channel_company_mapping = {}  # We'll populate this dynamically

@app.event("message")
def handle_message_events(body, logger):
    try:
        # Get the channel ID and message text
        channel_id = body["event"]["channel"]
        message_text = body["event"].get("text", "")
        user_id = body["event"].get("user", "")
        
        # Debug information
        print(f"\nReceived message in channel: {channel_id}")
        print(f"Message text: {message_text}")
        print(f"From user: {user_id}")
        print(f"Current channel mappings: {channel_company_mapping}")
        print(f"Full event body: {body}")  # Print full event for debugging
        
        # Ignore bot messages
        if "bot_id" in body["event"]:
            print("Ignoring bot message")
            return
        
        # Check if this is a set company command
        if message_text and message_text.lower().startswith("!set company"):
            try:
                # Extract company name from message
                company_name = message_text[12:].strip()  # Remove "!set company" and whitespace
                print(f"Attempting to set company to: {company_name}")
                
                # Validate company name
                if company_name not in ["Company A", "Company B", "Company C"]:
                    print(f"Invalid company name: {company_name}")
                    app.client.chat_postMessage(
                        channel=channel_id,
                        text="Invalid company name. Please use one of: Company A, Company B, Company C\nExample: !set company Company A"
                    )
                    return
                
                # Try to initialize the database to verify it works
                try:
                    db = create_qdrant_database(company_name)
                    if not db:
                        raise Exception("Failed to create or connect to database")
                except Exception as e:
                    print(f"Database initialization error: {str(e)}")
                    app.client.chat_postMessage(
                        channel=channel_id,
                        text="Error connecting to company database. Please try again later."
                    )
                    return
                
                # Update the channel-company mapping
                channel_company_mapping[channel_id] = company_name
                print(f"Updated channel mapping. New mappings: {channel_company_mapping}")
                
                app.client.chat_postMessage(
                    channel=channel_id,
                    text=f"✅ This channel has been associated with {company_name}"
                )
                return
                
            except Exception as e:
                logger.error(f"Error setting company: {str(e)}")
                print(f"Error in set company: {str(e)}")
                app.client.chat_postMessage(
                    channel=channel_id,
                    text="Error setting company. Please try again later."
                )
                return
        
        # Handle regular questions
        # Check if channel is mapped to a company
        if channel_id not in channel_company_mapping:
            print(f"Channel {channel_id} not mapped to any company")
            app.client.chat_postMessage(
                channel=channel_id,
                text="This channel is not associated with any company yet. Use '!set company [Company Name]' to set up the integration.\nExample: !set company Company A"
            )
            return
        
        # Get the company associated with this channel
        company = channel_company_mapping[channel_id]
        print(f"Processing question for company: {company}")
        
        try:
            # Initialize the vector database for the company
            db = create_qdrant_database(company)
            if not db:
                raise Exception("Failed to connect to database")
            
            # Search for relevant documents
            print(f"Searching for documents related to: {message_text}")
            related_documents = retrieve_docs(db, message_text, company)
            
            if not related_documents:
                print("No relevant documents found")
                app.client.chat_postMessage(
                    channel=channel_id,
                    text=f"I couldn't find any relevant information in {company}'s documents to answer your question."
                )
                return
            
            print(f"Found {len(related_documents)} relevant documents")
            # Generate answer using the question_pdf function
            answer = question_pdf(message_text, related_documents)
            
            # Send the response back to Slack
            app.client.chat_postMessage(
                channel=channel_id,
                text=f"Here's what I found:\n{answer}"
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            print(f"Error processing message: {str(e)}")
            app.client.chat_postMessage(
                channel=channel_id,
                text="I encountered an error while processing your question. Please try again later."
            )
    except Exception as e:
        print(f"Error handling message event: {str(e)}")
        logger.error(f"Error handling message event: {str(e)}")

@app.event("app_mention")
def handle_mentions(body, logger):
    print(f"Bot was mentioned: {body}")

def verify_slack_connection(app_instance):
    try:
        # Test API call
        response = app_instance.client.auth_test()
        print(f"\n✅ Successfully connected to Slack!")
        print(f"Bot User ID: {response['user_id']}")
        print(f"Bot Name: {response['user']}")
        print(f"Team Name: {response['team']}")
        return True
    except Exception as e:
        print(f"\n❌ Error connecting to Slack: {str(e)}")
        return False

def main():
    # Get the app token for Socket Mode
    app_token = os.environ.get("SLACK_APP_TOKEN")
    
    # Verify environment variables are loaded
    if not app_token:
        raise ValueError("SLACK_APP_TOKEN not found in environment variables")
    if not os.environ.get("SLACK_BOT_TOKEN"):
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")
    if not os.environ.get("SLACK_SIGNING_SECRET"):
        raise ValueError("SLACK_SIGNING_SECRET not found in environment variables")
    
    print("\n=== Starting Slack Bot ===")
    
    # Verify Slack connection
    if not verify_slack_connection(app):
        print("Failed to connect to Slack. Please check your tokens and permissions.")
        return
    
    print("\nAvailable commands:")
    print("  !set company [Company Name] - Associate the channel with a company")
    print("  Just type your question - Ask about company documents")
    print("\nWaiting for messages...")
    
    # Start the app in Socket Mode
    handler = SocketModeHandler(app, app_token)
    handler.start()

if __name__ == "__main__":
    main() 