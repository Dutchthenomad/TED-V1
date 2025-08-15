#!/usr/bin/env python3
"""
Analyze and visualize persistence data from MongoDB
Provides detailed health checks and data quality analysis
"""

import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
import pandas as pd
from typing import Dict, List
import json

class PersistenceAnalyzer:
    def __init__(self):
        # Connect to MongoDB
        self.client = MongoClient('mongodb://admin:password123@localhost:27017/rugs_tracker?authSource=admin')
        self.db = self.client.rugs_tracker
        
    def get_summary(self):
        """Get overall data summary"""
        print("\n" + "="*60)
        print(" TED PERSISTENCE DATA SUMMARY")
        print("="*60)
        
        collections = ['games', 'predictions', 'side_bets', 'tick_samples', 'metrics_hourly']
        
        for coll_name in collections:
            coll = self.db[coll_name]
            count = coll.count_documents({})
            
            # Get date range
            if count > 0:
                oldest = coll.find_one({}, sort=[("created_at", 1)])
                newest = coll.find_one({}, sort=[("created_at", -1)])
                
                if oldest and newest and 'created_at' in oldest and 'created_at' in newest:
                    date_range = f"{oldest['created_at'].strftime('%Y-%m-%d %H:%M')} to {newest['created_at'].strftime('%Y-%m-%d %H:%M')}"
                else:
                    date_range = "No timestamps"
            else:
                date_range = "Empty"
                
            print(f"\n📁 {coll_name.upper()}")
            print(f"   Documents: {count:,}")
            print(f"   Date Range: {date_range}")
            
            # Collection-specific stats
            if coll_name == 'games' and count > 0:
                completed = coll.count_documents({"end_tick": {"$ne": None}})
                avg_duration = list(coll.aggregate([
                    {"$match": {"duration_ticks": {"$ne": None}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$duration_ticks"}}}
                ]))
                if avg_duration:
                    print(f"   Completed: {completed}/{count} ({completed/count*100:.1f}%)")
                    print(f"   Avg Duration: {avg_duration[0]['avg']:.0f} ticks")
                    
            elif coll_name == 'predictions' and count > 0:
                with_outcomes = coll.count_documents({"actual_end_tick": {"$ne": None}})
                print(f"   With Outcomes: {with_outcomes:,} ({with_outcomes/count*100:.1f}%)")
    
    def analyze_prediction_quality(self):
        """Analyze prediction accuracy and error distribution"""
        print("\n" + "="*60)
        print(" PREDICTION QUALITY ANALYSIS")
        print("="*60)
        
        # Get predictions with outcomes
        pipeline = [
            {"$match": {"error_metrics": {"$exists": True}}},
            {"$project": {
                "game_id": 1,
                "predicted_end_tick": 1,
                "actual_end_tick": 1,
                "error": {"$subtract": ["$predicted_end_tick", "$actual_end_tick"]},
                "e40": "$error_metrics.e40",
                "absolute_error": "$error_metrics.absolute_error",
                "within_windows": "$error_metrics.within_windows",
                "confidence": 1
            }},
            {"$limit": 10000}  # Analyze last 10k predictions
        ]
        
        predictions = list(self.db.predictions.aggregate(pipeline))
        
        if not predictions:
            print("\n❌ No predictions with outcomes found")
            return
            
        df = pd.DataFrame(predictions)
        
        print(f"\n📊 Analyzing {len(df):,} predictions with outcomes")
        
        # Error distribution
        print("\n🎯 ERROR DISTRIBUTION:")
        print(f"   Mean Error: {df['error'].mean():.1f} ticks")
        print(f"   Std Dev: {df['error'].std():.1f} ticks")
        print(f"   Median Error: {df['error'].median():.1f} ticks")
        
        # E40 metrics
        print("\n📈 E40 METRICS (Window-Normalized Error):")
        print(f"   Mean E40: {df['e40'].mean():.3f}")
        print(f"   Median E40: {df['e40'].median():.3f}")
        print(f"   Std Dev: {df['e40'].std():.3f}")
        
        # Directional bias
        early = (df['error'] < 0).sum()
        late = (df['error'] > 0).sum()
        exact = (df['error'] == 0).sum()
        
        print("\n🎭 DIRECTIONAL BIAS:")
        print(f"   Early (predicted < actual): {early:,} ({early/len(df)*100:.1f}%)")
        print(f"   Late (predicted > actual): {late:,} ({late/len(df)*100:.1f}%)")
        print(f"   Exact: {exact:,} ({exact/len(df)*100:.1f}%)")
        
        # Window accuracy
        print("\n🎯 WINDOW ACCURACY:")
        for window in [1, 2, 3, 4, 5]:
            within = (df['within_windows'] <= window).sum()
            pct = within / len(df) * 100
            print(f"   Within {window} window{'s' if window > 1 else ''} (±{window*40} ticks): {pct:.1f}%")
        
        # Confidence calibration
        if 'confidence' in df.columns:
            print("\n🔮 CONFIDENCE CALIBRATION:")
            confidence_bins = pd.qcut(df['confidence'], q=5, duplicates='drop')
            for conf_range in confidence_bins.unique():
                mask = confidence_bins == conf_range
                if mask.sum() > 0:
                    accuracy = (df[mask]['within_windows'] <= 2).mean() * 100
                    print(f"   {conf_range}: {accuracy:.1f}% accuracy (n={mask.sum()})")
    
    def check_data_health(self):
        """Check for data quality issues"""
        print("\n" + "="*60)
        print(" DATA HEALTH CHECK")
        print("="*60)
        
        issues = []
        
        # Check for orphaned predictions
        game_ids = set(g['game_id'] for g in self.db.games.find({}, {"game_id": 1}))
        pred_game_ids = self.db.predictions.distinct("game_id")
        orphaned = set(pred_game_ids) - game_ids
        
        if orphaned:
            issues.append(f"⚠️ {len(orphaned)} predictions for non-existent games")
        
        # Check for games without predictions
        games_with_preds = self.db.predictions.distinct("game_id")
        games_without = game_ids - set(games_with_preds)
        
        if len(games_without) > 5:  # Allow some recent games
            issues.append(f"⚠️ {len(games_without)} games without any predictions")
        
        # Check for duplicate predictions
        pipeline = [
            {"$group": {
                "_id": {
                    "game_id": "$game_id",
                    "predicted_at_tick": "$predicted_at_tick",
                    "predicted_end_tick": "$predicted_end_tick"
                },
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}},
            {"$limit": 10}
        ]
        
        duplicates = list(self.db.predictions.aggregate(pipeline))
        if duplicates:
            total_dups = sum(d['count'] - 1 for d in duplicates)
            issues.append(f"⚠️ {total_dups} duplicate predictions found")
        
        # Check for missing error metrics
        total_completed = self.db.predictions.count_documents({"actual_end_tick": {"$ne": None}})
        with_metrics = self.db.predictions.count_documents({"error_metrics": {"$exists": True}})
        
        if total_completed > with_metrics:
            issues.append(f"⚠️ {total_completed - with_metrics} completed predictions missing error metrics")
        
        # Check for data gaps
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        recent_games = self.db.games.count_documents({"created_at": {"$gte": hour_ago}})
        
        if recent_games == 0:
            issues.append(f"⚠️ No games recorded in the last hour")
        
        # Report results
        if issues:
            print("\n❌ ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n✅ All health checks passed!")
        
        # Show collection sizes
        print("\n💾 STORAGE USAGE:")
        for coll_name in ['games', 'predictions', 'side_bets', 'tick_samples', 'metrics_hourly']:
            stats = self.db.command("collStats", coll_name)
            size_mb = stats['size'] / 1024 / 1024
            print(f"   {coll_name}: {size_mb:.2f} MB")
    
    def export_sample_data(self, output_dir="./data_samples"):
        """Export sample data for inspection"""
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n📥 Exporting sample data to {output_dir}/...")
        
        # Export recent games
        games = list(self.db.games.find({}, limit=10).sort("created_at", -1))
        with open(f"{output_dir}/sample_games.json", "w") as f:
            json.dump(games, f, default=str, indent=2)
        print(f"   ✓ Exported {len(games)} games")
        
        # Export predictions with metrics
        predictions = list(self.db.predictions.find(
            {"error_metrics": {"$exists": True}}, 
            limit=100
        ).sort("created_at", -1))
        with open(f"{output_dir}/sample_predictions.json", "w") as f:
            json.dump(predictions, f, default=str, indent=2)
        print(f"   ✓ Exported {len(predictions)} predictions")
        
        print(f"\n📁 Files saved in: {output_dir}/")

def main():
    analyzer = PersistenceAnalyzer()
    
    # Run all analyses
    analyzer.get_summary()
    analyzer.analyze_prediction_quality()
    analyzer.check_data_health()
    
    # Optional: export sample data
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        analyzer.export_sample_data()
    
    print("\n" + "="*60)
    print(" Analysis Complete!")
    print("="*60)

if __name__ == "__main__":
    main()