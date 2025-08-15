#!/bin/bash

# MongoDB Backup Script for TED System
# Creates local backups with timestamps and rotation

# Configuration
BACKUP_DIR="/mnt/c/Users/nomad/OneDrive/Desktop/GRAD_STUDIES/TED-V1-MONGO-BACKUP"
MONGO_CONTAINER="ted-mongodb"
DB_NAME="rugs_tracker"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ted_backup_${TIMESTAMP}"
KEEP_DAYS=7  # Keep backups for 7 days

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}     TED MongoDB Backup System                    ${NC}"
echo -e "${GREEN}==================================================${NC}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/current"

# Function to backup all collections
backup_full() {
    echo -e "\n${YELLOW}📦 Starting full database backup...${NC}"
    
    # Create backup inside container
    docker exec $MONGO_CONTAINER mongodump \
        -u admin -p password123 --authenticationDatabase admin \
        -d $DB_NAME \
        -o /tmp/$BACKUP_NAME \
        2>/dev/null
    
    if [ $? -eq 0 ]; then
        # Copy backup from container to local
        docker cp $MONGO_CONTAINER:/tmp/$BACKUP_NAME $BACKUP_DIR/current/
        
        # Clean up container temp files
        docker exec $MONGO_CONTAINER rm -rf /tmp/$BACKUP_NAME
        
        # Create compressed archive
        cd $BACKUP_DIR/current
        tar -czf ../${BACKUP_NAME}.tar.gz $BACKUP_NAME
        rm -rf $BACKUP_NAME
        cd - > /dev/null
        
        echo -e "${GREEN}✅ Backup completed: $BACKUP_DIR/${BACKUP_NAME}.tar.gz${NC}"
        
        # Show backup size
        SIZE=$(du -h $BACKUP_DIR/${BACKUP_NAME}.tar.gz | cut -f1)
        echo -e "${GREEN}   Size: $SIZE${NC}"
    else
        echo -e "${RED}❌ Backup failed!${NC}"
        exit 1
    fi
}

# Function to export to JSON (human-readable)
export_json() {
    echo -e "\n${YELLOW}📄 Exporting to JSON format...${NC}"
    
    JSON_DIR="$BACKUP_DIR/json_${TIMESTAMP}"
    mkdir -p "$JSON_DIR"
    
    # Export each collection
    for collection in games predictions side_bets metrics_hourly; do
        echo -e "   Exporting $collection..."
        docker exec $MONGO_CONTAINER mongoexport \
            -u admin -p password123 --authenticationDatabase admin \
            -d $DB_NAME -c $collection \
            --out /tmp/${collection}.json \
            2>/dev/null
        
        docker cp $MONGO_CONTAINER:/tmp/${collection}.json $JSON_DIR/
        docker exec $MONGO_CONTAINER rm /tmp/${collection}.json
    done
    
    echo -e "${GREEN}✅ JSON export completed: $JSON_DIR${NC}"
}

# Function to show backup statistics
show_stats() {
    echo -e "\n${YELLOW}📊 Current Database Statistics:${NC}"
    
    docker exec $MONGO_CONTAINER mongosh \
        -u admin -p password123 --authenticationDatabase admin \
        $DB_NAME --quiet --eval "
            var totalSize = 0;
            var collections = ['games', 'predictions', 'side_bets', 'metrics_hourly', 'tick_samples'];
            
            collections.forEach(function(name) {
                var count = db[name].countDocuments({});
                var stats = db[name].stats();
                totalSize += stats.size;
                print('   ' + name + ': ' + count + ' documents');
            });
            
            print('   Total size: ' + (totalSize/1024/1024).toFixed(2) + ' MB');
        "
}

# Function to clean old backups
cleanup_old() {
    echo -e "\n${YELLOW}🧹 Cleaning old backups (older than $KEEP_DAYS days)...${NC}"
    
    find $BACKUP_DIR -name "ted_backup_*.tar.gz" -mtime +$KEEP_DAYS -delete
    find $BACKUP_DIR -name "json_*" -type d -mtime +$KEEP_DAYS -exec rm -rf {} + 2>/dev/null
    
    # Count remaining backups
    COUNT=$(ls -1 $BACKUP_DIR/ted_backup_*.tar.gz 2>/dev/null | wc -l)
    echo -e "${GREEN}   Kept $COUNT backup(s)${NC}"
}

# Function to list existing backups
list_backups() {
    echo -e "\n${YELLOW}📁 Existing Backups:${NC}"
    if ls -1 $BACKUP_DIR/ted_backup_*.tar.gz 2>/dev/null | head -5; then
        echo "   ..."
        TOTAL=$(ls -1 $BACKUP_DIR/ted_backup_*.tar.gz 2>/dev/null | wc -l)
        echo -e "${GREEN}   Total: $TOTAL backups${NC}"
    else
        echo "   No backups found"
    fi
}

# Main execution
case "${1:-backup}" in
    backup)
        show_stats
        backup_full
        cleanup_old
        list_backups
        ;;
    
    json)
        show_stats
        export_json
        ;;
    
    both)
        show_stats
        backup_full
        export_json
        cleanup_old
        list_backups
        ;;
    
    restore)
        if [ -z "$2" ]; then
            echo -e "${RED}Usage: $0 restore <backup_file.tar.gz>${NC}"
            echo "Available backups:"
            ls -1 $BACKUP_DIR/ted_backup_*.tar.gz 2>/dev/null || echo "No backups found"
            exit 1
        fi
        
        echo -e "${YELLOW}⚠️  WARNING: This will restore data from backup!${NC}"
        echo -e "Backup to restore: $2"
        read -p "Continue? (y/N): " confirm
        
        if [ "$confirm" = "y" ]; then
            # Extract backup
            tar -xzf "$2" -C $BACKUP_DIR/current/
            BACKUP_FOLDER=$(basename "$2" .tar.gz)
            
            # Copy to container
            docker cp $BACKUP_DIR/current/$BACKUP_FOLDER $MONGO_CONTAINER:/tmp/
            
            # Restore
            docker exec $MONGO_CONTAINER mongorestore \
                -u admin -p password123 --authenticationDatabase admin \
                --drop \
                -d $DB_NAME \
                /tmp/$BACKUP_FOLDER/$DB_NAME
            
            # Cleanup
            docker exec $MONGO_CONTAINER rm -rf /tmp/$BACKUP_FOLDER
            rm -rf $BACKUP_DIR/current/$BACKUP_FOLDER
            
            echo -e "${GREEN}✅ Restore completed${NC}"
        fi
        ;;
    
    list)
        list_backups
        ;;
    
    *)
        echo "Usage: $0 [backup|json|both|restore|list]"
        echo "  backup  - Create compressed backup (default)"
        echo "  json    - Export to JSON format"
        echo "  both    - Create both backup and JSON"
        echo "  restore - Restore from backup"
        echo "  list    - List existing backups"
        exit 1
        ;;
esac

echo -e "\n${GREEN}==================================================${NC}"
echo -e "${GREEN} Backup operation completed successfully!         ${NC}"
echo -e "${GREEN}==================================================${NC}"