#!/bin/bash

# Script to view and explore persistence data in MongoDB
# Usage: ./view_persistence_data.sh [command]

MONGO_CMD="docker exec ted-mongodb mongosh -u admin -p password123 --authenticationDatabase admin rugs_tracker"

case "${1:-menu}" in
    menu)
        echo "==================================="
        echo "   TED Persistence Data Viewer    "
        echo "==================================="
        echo ""
        echo "1. Show collection statistics"
        echo "2. View recent games"
        echo "3. View recent predictions"
        echo "4. Show error metrics distribution"
        echo "5. Export data to JSON"
        echo "6. Interactive MongoDB shell"
        echo ""
        echo "Usage: $0 [stats|games|predictions|metrics|export|shell]"
        ;;
        
    stats)
        echo "📊 Collection Statistics:"
        $MONGO_CMD --eval "
            db.getCollectionNames().forEach(function(name) {
                var stats = db[name].stats();
                var count = db[name].countDocuments({});
                print('');
                print('Collection: ' + name);
                print('  Documents: ' + count);
                print('  Size: ' + (stats.size/1024/1024).toFixed(2) + ' MB');
                print('  Avg Doc Size: ' + (count > 0 ? (stats.avgObjSize/1024).toFixed(2) : 0) + ' KB');
                print('  Indexes: ' + stats.nindexes);
            });
        "
        ;;
        
    games)
        echo "🎮 Recent Games (Last 5):"
        $MONGO_CMD --eval "
            db.games.find({}, {
                game_id: 1, 
                start_tick: 1, 
                end_tick: 1, 
                duration_ticks: 1,
                peak_price: 1,
                final_price: 1,
                prediction_accuracy: 1
            })
            .sort({created_at: -1})
            .limit(5)
            .forEach(function(game) {
                print('');
                print('Game: ' + game.game_id);
                print('  Duration: ' + (game.duration_ticks || 'Running') + ' ticks');
                print('  Peak Price: ' + game.peak_price.toFixed(2));
                print('  Final Price: ' + (game.final_price ? game.final_price.toFixed(4) : 'N/A'));
                print('  Prediction Accuracy: ' + (game.prediction_accuracy ? (game.prediction_accuracy * 100).toFixed(1) + '%' : 'N/A'));
            });
        "
        ;;
        
    predictions)
        echo "🎯 Recent Predictions with Errors (Last 10):"
        $MONGO_CMD --eval "
            db.predictions.find(
                {actual_end_tick: {\$ne: null}},
                {
                    game_id: 1,
                    predicted_at_tick: 1,
                    predicted_end_tick: 1,
                    actual_end_tick: 1,
                    confidence: 1,
                    'error_metrics.e40': 1,
                    'error_metrics.within_windows': 1
                }
            )
            .sort({created_at: -1})
            .limit(10)
            .forEach(function(pred) {
                var error = pred.actual_end_tick - pred.predicted_end_tick;
                print('Predicted: ' + pred.predicted_end_tick + 
                      ' | Actual: ' + pred.actual_end_tick + 
                      ' | Error: ' + (error > 0 ? '+' : '') + error +
                      ' | E40: ' + pred.error_metrics.e40.toFixed(2) +
                      ' | Windows: ' + pred.error_metrics.within_windows);
            });
        "
        ;;
        
    metrics)
        echo "📈 Error Metrics Distribution:"
        $MONGO_CMD --eval "
            var pipeline = [
                {\$match: {'error_metrics.e40': {\$exists: true}}},
                {\$group: {
                    _id: null,
                    total: {\$sum: 1},
                    avg_e40: {\$avg: '\$error_metrics.e40'},
                    min_e40: {\$min: '\$error_metrics.e40'},
                    max_e40: {\$max: '\$error_metrics.e40'},
                    within_1_window: {\$sum: {\$cond: [{\$lte: ['\$error_metrics.within_windows', 1]}, 1, 0]}},
                    within_2_windows: {\$sum: {\$cond: [{\$lte: ['\$error_metrics.within_windows', 2]}, 1, 0]}},
                    within_3_windows: {\$sum: {\$cond: [{\$lte: ['\$error_metrics.within_windows', 3]}, 1, 0]}}
                }}
            ];
            
            var result = db.predictions.aggregate(pipeline).toArray()[0];
            if(result) {
                print('');
                print('Total Predictions with Outcomes: ' + result.total);
                print('');
                print('E40 Statistics:');
                print('  Average: ' + result.avg_e40.toFixed(3));
                print('  Min: ' + result.min_e40.toFixed(3));
                print('  Max: ' + result.max_e40.toFixed(3));
                print('');
                print('Accuracy by Windows:');
                print('  Within 1 window (±40 ticks): ' + (result.within_1_window/result.total*100).toFixed(1) + '%');
                print('  Within 2 windows (±80 ticks): ' + (result.within_2_windows/result.total*100).toFixed(1) + '%');
                print('  Within 3 windows (±120 ticks): ' + (result.within_3_windows/result.total*100).toFixed(1) + '%');
            }
        "
        ;;
        
    export)
        OUTPUT_DIR="./data_exports"
        mkdir -p $OUTPUT_DIR
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        
        echo "📥 Exporting data to $OUTPUT_DIR..."
        
        # Export games
        docker exec ted-mongodb mongoexport \
            -u admin -p password123 --authenticationDatabase admin \
            -d rugs_tracker -c games \
            --out /tmp/games_$TIMESTAMP.json
        docker cp ted-mongodb:/tmp/games_$TIMESTAMP.json $OUTPUT_DIR/
        echo "✓ Games exported to $OUTPUT_DIR/games_$TIMESTAMP.json"
        
        # Export predictions (last 1000)
        docker exec ted-mongodb mongoexport \
            -u admin -p password123 --authenticationDatabase admin \
            -d rugs_tracker -c predictions \
            --limit 1000 --sort '{created_at: -1}' \
            --out /tmp/predictions_$TIMESTAMP.json
        docker cp ted-mongodb:/tmp/predictions_$TIMESTAMP.json $OUTPUT_DIR/
        echo "✓ Predictions exported to $OUTPUT_DIR/predictions_$TIMESTAMP.json"
        
        echo ""
        echo "Files exported to: $OUTPUT_DIR/"
        ls -lh $OUTPUT_DIR/*.json | tail -2
        ;;
        
    shell)
        echo "🔧 Opening MongoDB Shell..."
        echo "Database: rugs_tracker"
        echo "Collections: games, predictions, side_bets, tick_samples, metrics_hourly"
        echo "Type 'exit' to quit"
        echo ""
        docker exec -it ted-mongodb mongosh -u admin -p password123 --authenticationDatabase admin rugs_tracker
        ;;
        
    *)
        echo "Unknown command: $1"
        echo "Usage: $0 [stats|games|predictions|metrics|export|shell]"
        exit 1
        ;;
esac