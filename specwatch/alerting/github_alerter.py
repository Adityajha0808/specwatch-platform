"""
GitHub alerter.
Creates GitHub issues for API changes.
"""

from typing import Optional
from github import Github, GithubException
from .alert_models import Alert, AlertResult, AlertChannel
from .alert_formatter import AlertFormatter
from specwatch.utils.logger import get_logger

logger = get_logger(__name__)

# GitHub issue alerter; Creates issues in a GitHub repository for API changes.
class GitHubAlerter:
    
    # Initialize GitHub alerter
    def __init__(self, token: str, repo: str):

        self.client = Github(token)
        self.repo = self.client.get_repo(repo)
        self.formatter = AlertFormatter()
        
        logger.info(f"GitHub alerter initialized for repo: {repo}")

    # Create GitHub issue for alert    
    def send_alert(self, alert: Alert) -> AlertResult:

        try:
            # Format as GitHub issue
            issue_data = self.formatter.format_github_issue(alert)
            
            logger.info(f"Creating GitHub issue for {alert.vendor} - {alert.endpoint_id}")
            
            # Create issue
            issue = self.repo.create_issue(
                title=issue_data['title'],
                body=issue_data['body'],
                labels=issue_data['labels']
            )
            
            logger.info(f"GitHub issue created: #{issue.number}")
            
            return AlertResult(
                channel=AlertChannel.GITHUB,
                success=True,
                message=f"Issue #{issue.number} created",
                metadata={
                    'issue_number': issue.number,
                    'issue_url': issue.html_url
                }
            )
        
        except GithubException as e:
            logger.error(f"GitHub API error: {e.status} - {e.data.get('message', 'Unknown error')}")
            return AlertResult(
                channel=AlertChannel.GITHUB,
                success=False,
                message=f"GitHub API error: {e.data.get('message', 'Unknown error')}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error creating GitHub issue: {str(e)}")
            return AlertResult(
                channel=AlertChannel.GITHUB,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    # Add comment to existing issue
    def add_comment(self, issue_number: int, comment: str) -> bool:

        try:
            issue = self.repo.get_issue(issue_number)
            issue.create_comment(comment)
            logger.info(f"Comment added to issue #{issue_number}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding comment to issue #{issue_number}: {str(e)}")
            return False
    
    # Close an issue
    def close_issue(self, issue_number: int, comment: Optional[str] = None) -> bool:

        try:
            issue = self.repo.get_issue(issue_number)
            
            if comment:
                issue.create_comment(comment)
            
            issue.edit(state='closed')
            logger.info(f"Issue #{issue_number} closed")
            return True
        
        except Exception as e:
            logger.error(f"Error closing issue #{issue_number}: {str(e)}")
            return False

    # Find existing open issue for this endpoint    
    def find_existing_issue(self, vendor: str, endpoint_id: str) -> Optional[int]:

        try:
            # Search for open issues with endpoint ID in body
            issues = self.repo.get_issues(state='open', labels=[vendor.lower()])
            
            for issue in issues:
                if endpoint_id in issue.body:
                    return issue.number
            
            return None
        
        except Exception as e:
            logger.error(f"Error searching for existing issue: {str(e)}")
            return None
