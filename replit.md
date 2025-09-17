# Overview

This project is an Arabic-focused search and information aggregation service built with FastAPI. It provides intelligent search capabilities specifically designed for Arabic content, featuring smart summarization, price comparison from various marketplaces, image search, content rating, PDF generation, and a night mode interface. The application acts as a comprehensive Arabic search engine with enhanced features for better user experience in Arabic-speaking regions.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **FastAPI**: Chosen as the primary web framework for its high performance, automatic API documentation, and modern Python async capabilities
- **Uvicorn**: ASGI server for running the FastAPI application

## Search Engine Integration
- **DuckDuckGo Search (DDGS)**: Primary search provider to avoid API rate limits and costs while maintaining privacy
- **Custom Arabic Detection**: Uses regex pattern matching to identify Arabic content with minimum character thresholds
- **Domain Prioritization**: Implements preferred Arabic domains (Wikipedia, Mawdoo3, Al Jazeera, etc.) for culturally relevant results

## Content Processing Pipeline
- **Readability**: Extracts clean, readable content from web pages by removing ads and navigation elements
- **BeautifulSoup**: HTML parsing and content extraction for detailed text analysis
- **Smart Answer Engine**: Custom question-answering system that categorizes queries (definition, how-to, why, when, where, who, quantity, yes/no) for targeted responses

## Caching Strategy
- **DiskCache**: File-based caching system to store search results and processed content
- Reduces API calls and improves response times for repeated queries
- Persistent storage across application restarts

## Market Integration
- **Multi-marketplace Support**: Integrated price comparison across major platforms including Alibaba, Amazon variants, Noon, Jumia, eBay, and regional marketplaces
- **Localized Shopping**: Focus on Middle Eastern and Arabic region marketplaces (Amazon.ae, Amazon.sa, Noon.com)

## Content Generation
- **FPDF**: PDF generation capability for saving search results and summaries
- **Content Summarization**: Intelligent text processing for creating concise summaries of Arabic content

## Language Processing
- **Arabic Text Detection**: Custom regex-based Arabic character detection with configurable thresholds
- **Multilingual Support**: Handles both Arabic and English content with appropriate processing for each language

## Request Handling
- **Custom Headers**: Uses branded user-agent ("BassamBot") for web scraping compliance
- **Form Processing**: Supports both form-based and JSON API interactions
- **Error Handling**: Implements robust error handling for network requests and content processing

# External Dependencies

## Search Services
- **DuckDuckGo Search API**: Primary search provider for web results, images, and news
- No API keys required, providing unrestricted access to search functionality

## Content Processing Libraries
- **Readability-lxml**: Extracts main content from web pages
- **BeautifulSoup4**: HTML parsing and manipulation
- **Requests**: HTTP client for web scraping and API calls

## Document Generation
- **FPDF2/FPDF**: PDF generation for exporting search results and summaries

## Storage and Caching
- **DiskCache**: Local file-based caching system for performance optimization

## Web Framework Stack
- **FastAPI**: Modern, fast web framework with automatic API documentation
- **Uvicorn**: ASGI server for production deployment
- **Python-multipart**: Form data handling for file uploads and complex forms

## Marketplace APIs
- Integration points for major e-commerce platforms (Amazon, Alibaba, eBay, Noon, Jumia)
- Uses web scraping approach rather than official APIs to avoid rate limiting and access restrictions