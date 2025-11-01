# Community Features Documentation

## Overview

The KingdomPay system now includes comprehensive community management functionality that allows users to create, join, and manage communities with financial contributions and transactions.

## Database Schema

### New Tables Added

#### 1. Communities Table

- **Purpose**: Stores information about different communities
- **Key Fields**:
  - `id`: Primary key
  - `community_id`: UUID for external references
  - `name`: Community name
  - `description`: Community description
  - `type`: Community type (e.g., 'savings', 'investment', 'social')
  - `created_by`: Foreign key to users table
  - `created_at`, `updated_at`: Timestamps

#### 2. Community Roles Table

- **Purpose**: Defines different roles that can be assigned to community members
- **Key Fields**:
  - `id`: Primary key
  - `role_id`: UUID for external references
  - `role_name`: Role name (admin, moderator, member, treasurer, secretary)
  - `description`: Role description

#### 3. Community Members Table

- **Purpose**: Junction table linking users to communities with role information
- **Key Fields**:
  - `id`: Primary key
  - `user_id`: Foreign key to users table
  - `community_id`: Foreign key to communities table
  - `role_id`: Foreign key to community_roles table
  - `role`: Fallback role name
  - `joined_at`: When user joined the community
  - `is_active`: Whether membership is active

#### 4. Contributions Table

- **Purpose**: Records financial contributions made by users to communities
- **Key Fields**:
  - `id`: Primary key
  - `user_id`: Foreign key to users table
  - `community_id`: Foreign key to communities table
  - `amount`: Contribution amount
  - `contribution_type`: Type of contribution (monthly, one-time, emergency)
  - `description`: Contribution description
  - `created_at`: When contribution was made

### Updated Tables

#### Transactions Table

- **New Field**: `contribution_id` - Links transactions to contributions
- **Purpose**: Track financial transactions related to community contributions

#### Users Table

- **New Relationships**:
  - `community_memberships`: User's community memberships
  - `contributions`: User's contributions to communities

## Relationships

### Entity Relationship Diagram

```
Users (1) ←→ (M) CommunityMembers (M) ←→ (1) Communities
Users (1) ←→ (M) Contributions (M) ←→ (1) Communities
Contributions (1) ←→ (M) Transactions
CommunityRoles (1) ←→ (M) CommunityMembers
```

### Key Relationships

1. **Users ↔ Communities**: Many-to-many through CommunityMembers
2. **Users ↔ Contributions**: One-to-many (users make contributions)
3. **Communities ↔ Contributions**: One-to-many (communities receive contributions)
4. **Contributions ↔ Transactions**: One-to-many (contributions tracked by transactions)
5. **CommunityRoles ↔ CommunityMembers**: One-to-many (roles assigned to members)

## API Endpoints (To Be Implemented)

### Community Management

- `POST /api/v1/communities` - Create a new community
- `GET /api/v1/communities` - List communities
- `GET /api/v1/communities/{id}` - Get community details
- `PUT /api/v1/communities/{id}` - Update community
- `DELETE /api/v1/communities/{id}` - Delete community

### Community Membership

- `POST /api/v1/communities/{id}/join` - Join a community
- `POST /api/v1/communities/{id}/leave` - Leave a community
- `GET /api/v1/communities/{id}/members` - List community members
- `PUT /api/v1/communities/{id}/members/{user_id}` - Update member role

### Contributions

- `POST /api/v1/communities/{id}/contributions` - Make a contribution
- `GET /api/v1/communities/{id}/contributions` - List community contributions
- `GET /api/v1/users/{id}/contributions` - List user contributions

### Community Roles

- `GET /api/v1/community-roles` - List available roles
- `POST /api/v1/community-roles` - Create new role (admin only)

## Usage Examples

### Creating a Community

```python
from models.community import Community

# Create a new community
community = Community(
    name="Savings Group Alpha",
    description="Monthly savings group for emergency funds",
    type="savings",
    created_by=user_id
)
db.session.add(community)
db.session.commit()
```

### Joining a Community

```python
from models.community import CommunityMember, CommunityRole

# Join a community as a regular member
membership = CommunityMember(
    user_id=user_id,
    community_id=community_id,
    role_id=3  # member role
)
db.session.add(membership)
db.session.commit()
```

### Making a Contribution

```python
from models.community import Contribution

# Make a contribution to a community
contribution = Contribution(
    user_id=user_id,
    community_id=community_id,
    amount=1000.00,
    contribution_type="monthly",
    description="Monthly savings contribution"
)
db.session.add(contribution)
db.session.commit()
```

## Migration Instructions

### Running the Migration

```bash
# Run the migration script
python migrate_community_tables.py

# To rollback (use with caution!)
python migrate_community_tables.py rollback
```

### Manual SQL Migration

```bash
# Run the SQL file directly
psql -d your_database -f db/community_tables.sql
```

## Default Data

The migration script automatically creates default community roles:

- **admin**: Community administrator with full management rights
- **moderator**: Community moderator with limited management rights
- **member**: Regular community member
- **treasurer**: Community treasurer responsible for financial management
- **secretary**: Community secretary responsible for record keeping

## Security Considerations

1. **Access Control**: Only community admins can modify community settings
2. **Financial Security**: All contributions are tracked through the transaction system
3. **Data Integrity**: Foreign key constraints ensure data consistency
4. **Audit Trail**: All contributions are linked to transactions for audit purposes

## Performance Optimizations

1. **Indexes**: All foreign keys and frequently queried fields are indexed
2. **Cascading Deletes**: Proper cascade rules prevent orphaned records
3. **Query Optimization**: Helper methods for common queries are provided

## Future Enhancements

1. **Community Analytics**: Track contribution patterns and community growth
2. **Automated Contributions**: Recurring contribution scheduling
3. **Community Goals**: Set and track community financial goals
4. **Notifications**: Real-time notifications for community activities
5. **Mobile App Integration**: Native mobile app support for community features
