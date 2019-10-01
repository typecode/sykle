from typing import Dict
import git
import github


class SCM:
    """A bridge between:
    git.Repo,
    github.Github,
    github.Organization,
    github.Repository,
    github.Branch,
    github.Team, and
    github.User.

    Responsible for initializing github repositories with
    default settings.

    TODO: Add jira webhook to the default webhook configs.
    """

    MASTER_BRANCH_NAME = 'master'
    DEVELOPMENT_BRANCH_NAME = 'develop'

    DEFAULT_BOT_TEAM_SLUG = 'bots'
    DEFAULT_TEAM_SLUG = 'typecode-developers'

    DEFAULT_WEBHOOK_CONFIGS = {
        'web': {
            'config': {
                'url': 'https://smash.typeco.de/github-webhook/',
                'content_type': 'form',
                'insecure_ssl': 0
            },
            'events': ['push', 'pull_request'],
            'active': True
        }
    }

    def __init__(self, org, token):
        self.github = github.Github(token)
        self.user = self.github.get_user()
        self.org = self.github.get_organization(org)
        self.repo = None
        self._org_owners = None
        self._default_team = None
        self._default_bots_team = None

    def create_repo(self, name):
        """Create a github repo and store it on the object."""
        self.repo = self.org.create_repo(name, auto_init=True, private=True)

    def clone_repo(self):
        """Clone the current repo into the cwd."""
        git.Repo.clone_from(self.repo.ssh_url, self.repo.name)

    def create_branch(self, source_branch_name, target_branch_name):
        if not self.repo:
            raise Exception('Can\'t create a branch without a repo')

        master_branch = self.repo.get_branch(source_branch_name)
        new_ref = 'refs/heads/%s' % target_branch_name
        self.repo.create_git_ref(
            ref=new_ref, sha=master_branch.commit.sha)

    def create_default_development_branch(self):
        self.create_branch(
            self.MASTER_BRANCH_NAME, self.DEVELOPMENT_BRANCH_NAME)
        self.repo.edit(
            default_branch=self.DEVELOPMENT_BRANCH_NAME
        )

    def get_org_owners(self):
        return [
            member.login for member in self.org.get_members(role='admin')
        ]

    @property
    def org_owners(self):
        if not self._org_owners:
            self._org_owners = self.get_org_owners()
        return self._org_owners

    @property
    def default_team(self):
        if not self._default_team:
            self._default_team = self.org.get_team_by_slug(
                self.DEFAULT_TEAM_SLUG)
        return self._default_team

    @property
    def default_bots_team(self):
        if not self._default_bots_team:
            self._default_bots_team = self.org.get_team_by_slug(
                self.DEFAULT_BOT_TEAM_SLUG)
        return self._default_bots_team

    @property
    def default_team_members(self):
        return self.default_team.get_members()

    def create_branch_protections(self):
        for branch_name in [
            self.MASTER_BRANCH_NAME, self.DEVELOPMENT_BRANCH_NAME
        ]:
            branch = self.repo.get_branch(branch_name)
            branch.edit_protection(
                # Require branches to be up to date before merging.
                strict=True,
                # Administrators are not subject to restrictions.
                enforce_admins=True,
                # Require at least one approving review before
                # allowing a PR to merge.
                dismissal_users=self.org_owners,
                # Dismiss reviews when new commits are made.
                dismiss_stale_reviews=True,
                require_code_owner_reviews=True,
                required_approving_review_count=1,
                user_push_restrictions=[
                    member.login for member in self.default_team_members
                ]

            )

    def create_webhooks(self, hook_configs: Dict[str, Dict] = None):
        hook_configs = hook_configs or self.DEFAULT_WEBHOOK_CONFIGS
        for name, config in hook_configs.items():
            self.repo.create_hook(name, **config)

    def add_default_teams_to_repo(self):
        if not self.repo:
            raise Exception('Can\'t add team to nonexistent repo')

        self.default_team.add_to_repos(self.repo)
        self.default_bots_team.add_to_repos(self.repo)
