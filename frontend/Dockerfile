FROM nginx:alpine

# Remove ALL default nginx files
RUN rm -rf /usr/share/nginx/html/*

# Remove default config
RUN rm -rf /etc/nginx/conf.d/*

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy ONLY frontend build (not everything blindly)
COPY . /usr/share/nginx/html