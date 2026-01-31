# Computer Students Hub (CSH)

A unified web platform where undergraduate computer science students can browse curated courses, labs, resources, and learning roadmaps.

## Overview

Computer Students Hub (CSH) is designed to deliver a comprehensive learning platform that helps computer science students navigate their academic journey. Guests can explore content without logging in, while registered users can bookmark, comment, rate, and participate in Q&A discussions.

## Key Features

### For Students
- **Browse Curated Content** - Access courses, labs, and resources organized by levels and semesters
- **Learning Pathways** - Follow structured roadmaps to guide your learning journey
- **Interactive Q&A** - Ask questions, provide answers, and engage with the community
- **Bookmarking** - Save important resources for quick access later
- **Rating & Comments** - Share feedback and insights on courses and resources

### For Instructors
- **Content Creation** - Create and edit courses, labs, and resources
- **Community Engagement** - Participate in discussions and help students

### For Administrators
- **Content Management** - Review, approve, and publish content
- **User Management** - Manage roles and permissions
- **Analytics** - Track platform usage and engagement

## Technical Architecture

### MVP Scope
- **Language**: English-only interface
- **Roles**: Guest, Student, Instructor, and Admin with role-based access control
- **Focus**: Content distribution and community discussion (not a full LMS)

### Technology Stack

#### Backend
- **Framework**: Django (REST APIs)
- **Architecture**: Modular design
- **Database**: PostgreSQL (accessed via Prisma ORM)
- **Schema**: Relational structure supporting hierarchical data and many-to-many relations

#### Module Structure
```
modules/
├── auth/           # Authentication (controllers/services/guards)
├── users/          # User and role management
├── courses/        # Levels, semesters, courses/labs
├── resources/      # Resources and assignments
├── pathways/       # Learning pathways
├── qna/            # Questions, answers, votes and comments
├── bookmarks/      # User bookmarks
├── notifications/  # Notification handling
├── submissions/    # Content improvement submissions and draft workflows
├── tags/           # Tag CRUD operations
└── admin/          # Drive import, audit logs, analytics
```

## MVP Exclusions

The following features are **not** included in the initial MVP:
- Multi-tenancy support
- Gamification features
- Grade management
- Assignment submissions
- Multi-language support

## User Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Guest** | Browse and view public content |
| **Student** | Browse, bookmark, comment, rate, participate in Q&A |
| **Instructor** | Create and edit content, engage in discussions |
| **Admin** | Full content management, user management, publishing rights |

## Getting Started

### Prerequisites
- Python 3.x
- PostgreSQL
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yasserhegazy/Computer-Students-Hub.git
cd Computer-Students-Hub
```

2. Create and activate virtual environment:
```bash
python -m venv myenv
# On Windows
myenv\Scripts\activate
# On Unix/MacOS
source myenv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
