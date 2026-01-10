import os
import re
import git
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class GradleBuildResult:
    build_version: Optional[str] = None
    artifact_urls: List[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    
class GradleBuild:
    def process(self, checkout_result: Any, task_name: str) -> GradleBuildResult:
        """
        Build the Gradle project and push Docker images.
        
        Args:
            checkout_result: Result from CheckoutMerged step containing branch info
            task_name: Name of the Gradle task to execute
            
        Returns:
            GradleBuildResult: Object with build results and Docker image info
        """
        if not checkout_result.success or not checkout_result.branch_name:
            return GradleBuildResult(
                success=False,
                error_message="Cannot build: checkout failed"
            )
        
        try:
            # Create a new temporary folder for the checkout
            with tempfile.TemporaryDirectory(prefix="brencher_build_") as build_dir:
                # Clone the repository and checkout the merged branch
                repo_url = os.getenv('GIT_REPO_URL')
                if not repo_url:
                    return GradleBuildResult(
                        success=False,
                        error_message="GIT_REPO_URL environment variable is not set"
                    )
                
                # Clone with authentication if needed
                auth_url = self._get_auth_git_url(repo_url)
                repo = git.Repo.clone_from(auth_url, build_dir)
                repo.git.checkout(checkout_result.branch_name)
                
                # Calculate build version from commit hash
                build_version = checkout_result.commit_hash[:5] if checkout_result.commit_hash else "dev"
                logger.info(f"Using build version: {build_version}")
                
                # Update version in gradle.properties
                self._update_gradle_version(build_dir, build_version)
                
                # Extract Docker image names from the project
                docker_images = self._extract_docker_images(build_dir)
                
                # Check if images exist in registry
                images_exist = self._check_images_exist(docker_images, build_version)
                
                if not images_exist:
                    # Execute gradle jib task
                    logger.info(f"Executing Gradle task: {task_name}")
                    result = self._run_gradle_task(build_dir, task_name)
                    
                    if not result.success:
                        return result
                
                # Format image URLs
                artifact_urls = [f"{img}:{build_version}" for img in docker_images]
                
                return GradleBuildResult(
                    build_version=build_version,
                    artifact_urls=artifact_urls,
                    success=True
                )

        except Exception as e:
            error_message = f"Gradle build failed: {str(e)}"
            logger.error(error_message)
            
            return GradleBuildResult(
                success=False,
                error_message=error_message
            )
    
    def _get_auth_git_url(self, url: str) -> str:
        username = os.getenv('GIT_USERNAME')
        password = os.getenv('GIT_PASSWORD')
        
        if username and password:
            # Extract protocol and the rest of the URL
            protocol, rest = url.split('://')
            return f"{protocol}://{username}:{password}@{rest}"
        
        return url
    
    def _update_gradle_version(self, project_dir: str, version: str) -> None:
        """Update the version in gradle.properties"""
        properties_file = os.path.join(project_dir, 'gradle.properties')
        
        if os.path.exists(properties_file):
            with open(properties_file, 'r') as f:
                content = f.read()
            
            # Replace or add version property
            if re.search(r'version\s*=', content):
                content = re.sub(r'version\s*=\s*[^\n]*', f'version={version}', content)
            else:
                content += f'\nversion={version}\n'
            
            with open(properties_file, 'w') as f:
                f.write(content)

            logger.info(f"Updated version to {version} in gradle.properties")

    def _extract_docker_images(self, project_dir: str) -> List[str]:
        """Extract Docker image names from Gradle modules"""
        images = []

        # Look for build.gradle or build.gradle.kts files
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if file in ('build.gradle', 'build.gradle.kts'):
                    file_path = os.path.join(root, file)
                    
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Look for Docker image definitions in jib configurations
                    image_matches = re.findall(r'image\s*=\s*[\'"]([^\'"]*)[\'"]\s*', content)
                    if image_matches:
                        images.extend(image_matches)
        
        return list(set(images))  # Remove duplicates

    def _check_images_exist(self, images: List[str], version: str) -> bool:
        """Check if Docker images with the given version exist in the registry"""
        # For demonstration purposes, we'll assume images don't exist
        # In a real implementation, you would check against your Docker registry
        return False

    def _run_gradle_task(self, project_dir: str, task_name: str) -> GradleBuildResult:
        """Run a Gradle task in the project directory"""
        try:
            # Check if wrapper exists
            wrapper_script = 'gradlew.bat' if os.name == 'nt' else './gradlew'
            if os.path.exists(os.path.join(project_dir, 'gradlew')):
                # Make gradlew executable
                os.chmod(os.path.join(project_dir, 'gradlew'), 0o755)
                gradle_cmd = [wrapper_script, task_name]
            else:
                # Use global gradle
                gradle_cmd = ['gradle', task_name]

            # Run the command
            logger.info(f"Running Gradle command: {' '.join(gradle_cmd)}")
            result = subprocess.run(
                gradle_cmd,
                cwd=project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return GradleBuildResult(
                    success=False,
                    error_message=f"Gradle task failed: {result.stderr}"
                )

            return GradleBuildResult(success=True)

        except Exception as e:
            return GradleBuildResult(
                success=False,
                error_message=f"Failed to run Gradle task: {str(e)}"
            )
