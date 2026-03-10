// src/components/ServicesSection.js
import React from 'react';
import { useNavigate } from 'react-router-dom';

function ServicesSection() {
  const navigate = useNavigate();

  const services = [
    {
      id: 1,
      icon: 'fa-solid fa-robot',
      title: 'AI Answer Evaluation',
      description: 'Intelligent grading using deep learning models with semantic understanding, NLI reasoning, and custom ANN for accurate scoring.',
      link: '/evaluate',
      status: 'active',
      color: '#667eea'
    },
    {
      id: 2,
      icon: 'fa-solid fa-brain',
      title: 'AI Answer using RAG',
      description: 'Generate context-aware reference answers using Retrieval-Augmented Generation from your knowledge base documents.',
      link: '#rag-answer',
      status: 'coming-soon',
      color: '#10b981'
    },
    {
      id: 3,
      icon: 'fa-solid fa-file-image',
      title: 'OCR Answer Extraction',
      description: 'Extract handwritten or printed text from answer sheets using advanced OCR technology for automated processing.',
      link: '#ocr-extraction',
      status: 'coming-soon',
      color: '#f59e0b'
    }
  ];

  const handleServiceClick = (service) => {
    if (service.status === 'active') {
      // Navigate to the service
      navigate(service.link);
    } else {
      // Show coming soon message
      alert(`${service.title} - Coming Soon!\n\nThis feature is under development and will be available in the next update.`);
    }
  };

  return (
    <section id="services" className="services-section">
      <div className="services-container">
        
        {/* Section Header */}
        <div className="services-header">
          <h2 className="services-title">
            <i className="fa-solid fa-star"></i>
            Our Services
          </h2>
          <p className="services-subtitle">
            Comprehensive AI-powered evaluation tools designed for modern education
          </p>
        </div>

        {/* Services Grid */}
        <div className="services-grid">
          {services.map((service) => (
            <div 
              key={service.id} 
              className={`service-card ${service.status}`}
              onClick={() => handleServiceClick(service)}
              style={{ '--service-color': service.color }}
            >
              {/* Status Badge */}
              {service.status !== 'active' && (
                <div className="service-badge">
                  {service.status === 'coming-soon' ? 'Coming Soon' : 'Planned'}
                </div>
              )}

              {/* Icon */}
              <div className="service-icon">
                <i className={service.icon}></i>
              </div>

              {/* Content */}
              <div className="service-content">
                <h3 className="service-title">{service.title}</h3>
                <p className="service-description">{service.description}</p>
              </div>

              {/* Arrow */}
              <div className="service-arrow">
                <i className="fa-solid fa-arrow-right"></i>
              </div>
            </div>
          ))}
        </div>

        {/* Info Banner */}
        <div className="services-info">
          <i className="fa-solid fa-info-circle"></i>
          <p>
            Start with AI Answer Evaluation now. RAG-based answer generation and OCR extraction features are coming soon to enhance your grading workflow.
          </p>
        </div>

      </div>
    </section>
  );
}

export default ServicesSection;
