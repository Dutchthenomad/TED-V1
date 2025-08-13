FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Check if yarn.lock exists and copy it if it does
COPY yarn.lock* ./

# Install dependencies (without frozen lockfile to allow updates)
RUN yarn install

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application in development mode
CMD ["yarn", "start"]