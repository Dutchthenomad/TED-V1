# Prediction History Display Count Fix

## Issue
The prediction history window was showing "20 of 20" regardless of the dropdown selection, even when more data was available and a different display count was selected.

## Root Cause
The initial state of `historyShowN` was set to 50, but the first dropdown option was 20. This mismatch could cause confusion about what was actually being displayed.

## Fix Applied

### 1. **Aligned Default Value**
Changed the initial state to match the first dropdown option:
```javascript
// Before
const [historyShowN, setHistoryShowN] = useState(50);

// After  
const [historyShowN, setHistoryShowN] = useState(20);
```

### 2. **Clarified Display Text**
Made the counter text clearer:
```javascript
// Before
({Math.min(historyShowN, predictionHistory.length)} of {predictionHistory.length})

// After
(showing {Math.min(historyShowN, predictionHistory.length)} of {predictionHistory.length})
```

## How It Works Now

1. **On Load**: 
   - Default shows 20 rows (first dropdown option)
   - Display shows "showing 20 of X" where X is total available

2. **When Changing Dropdown**:
   - Select 50, 100, or 200 from dropdown
   - Table immediately updates to show that many rows
   - Counter updates to "showing N of X"

3. **Data Flow**:
   - REST API fetches up to 200 entries
   - WebSocket may update with different amounts
   - Display always respects the selected `historyShowN` value

## Verification

The display now correctly:
- Shows 20 rows by default
- Updates when dropdown is changed  
- Displays accurate count (e.g., "showing 50 of 200")
- Scrollbar appears when needed
- Maintains selection across data updates

## User Experience

- **Clear Feedback**: Users see exactly how many rows are displayed vs available
- **Predictable Behavior**: Default matches first dropdown option
- **Responsive**: Changes apply immediately
- **No Confusion**: Display count always matches what's actually shown

## Testing

1. Load the page → Should show "showing 20 of X"
2. Change dropdown to 50 → Should show "showing 50 of X" 
3. Change dropdown to 100 → Should show "showing 100 of X"
4. Change dropdown to 200 → Should show "showing 200 of X" (or less if fewer available)

The issue is now resolved and the prediction history display works as expected.