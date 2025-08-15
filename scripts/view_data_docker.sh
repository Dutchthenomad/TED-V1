#!/bin/bash

# Quick data viewer using Docker
echo "============================================"
echo "       TED PERSISTENCE DATA VIEWER         "
echo "============================================"

# Show collection sizes and document counts
echo -e "\n📊 DATA OVERVIEW:"
docker exec ted-mongodb mongosh -u admin -p password123 --authenticationDatabase admin rugs_tracker --quiet --eval "
    db.getCollectionNames().forEach(function(name) {
        var count = db[name].countDocuments({});
        var stats = db[name].stats();
        var sizeMB = (stats.size / 1024 / 1024).toFixed(2);
        print(name.padEnd(20) + count.toString().padStart(8) + ' docs' + sizeMB.padStart(10) + ' MB');
    });
"

# Show recent games
echo -e "\n🎮 RECENT GAMES (Last 3):"
docker exec ted-mongodb mongosh -u admin -p password123 --authenticationDatabase admin rugs_tracker --quiet --eval "
    db.games.find({}, {
        game_id: 1,
        duration_ticks: 1,
        peak_price: 1,
        end_tick: 1
    }).sort({created_at: -1}).limit(3).forEach(function(g) {
        var status = g.end_tick ? 'Completed (' + g.duration_ticks + ' ticks)' : 'Running';
        print('  ' + g.game_id.substring(0,20) + '... | ' + status + ' | Peak: ' + g.peak_price.toFixed(2));
    });
"

# Show prediction accuracy
echo -e "\n🎯 PREDICTION ACCURACY:"
docker exec ted-mongodb mongosh -u admin -p password123 --authenticationDatabase admin rugs_tracker --quiet --eval "
    var stats = db.predictions.aggregate([
        {\$match: {'error_metrics.e40': {\$exists: true}}},
        {\$group: {
            _id: null,
            count: {\$sum: 1},
            avg_e40: {\$avg: '\$error_metrics.e40'},
            within_1: {\$sum: {\$cond: [{\$lte: [{\$abs: '\$error_metrics.within_windows'}, 1]}, 1, 0]}},
            within_2: {\$sum: {\$cond: [{\$lte: [{\$abs: '\$error_metrics.within_windows'}, 2]}, 1, 0]}}
        }}
    ]).toArray()[0];
    
    if(stats) {
        print('  Total Evaluated: ' + stats.count);
        print('  Average E40: ' + stats.avg_e40.toFixed(3));
        print('  Within 1 Window: ' + (stats.within_1/stats.count*100).toFixed(1) + '%');
        print('  Within 2 Windows: ' + (stats.within_2/stats.count*100).toFixed(1) + '%');
    }
"

# Show data freshness
echo -e "\n⏱️ DATA FRESHNESS:"
docker exec ted-mongodb mongosh -u admin -p password123 --authenticationDatabase admin rugs_tracker --quiet --eval "
    var latest_game = db.games.findOne({}, {created_at: 1}, {sort: {created_at: -1}});
    var latest_pred = db.predictions.findOne({}, {created_at: 1}, {sort: {created_at: -1}});
    
    if(latest_game) {
        var game_age = Math.floor((new Date() - latest_game.created_at) / 1000 / 60);
        print('  Latest Game: ' + game_age + ' minutes ago');
    }
    if(latest_pred) {
        var pred_age = Math.floor((new Date() - latest_pred.created_at) / 1000 / 60);
        print('  Latest Prediction: ' + pred_age + ' minutes ago');
    }
"

echo -e "\n============================================"
echo "To explore data interactively, run:"
echo "  ./scripts/view_persistence_data.sh shell"
echo "============================================"